# --------------------------------------------------------
# File: src/world/world.py
"""
World object: coordinates the map fields, biome classification and resource grid.

Responsabilità:
  - generare / caricare la mappa (elevation, temperature, humidity, pressure)
  - classificare i biomi a partire dai campi fisici + stato biologico lento
  - esporre input ambientali ai pixel
  - tenere traccia di strati organici / minerali e gas globali

Nota importante:
  La riclassificazione dei biomi è ora *event‑driven*:
  - all'avvio facciamo una classificazione completa
  - in seguito aggiorniamo solo le celle segnate come "sporche"
    (es. quando muoiono pixel e depositano biomassa), per evitare
    muri di calcolo periodici.
"""

from typing import Optional, Tuple, Dict
import os

import numpy as np

from .map_generator import MapGenerator
from .biome import biome_from_env, Biome, color_for_biome
from .environment import sample_environment, ENV_CHANNELS


class World:
    def __init__(
        self,
        size: Tuple[int, int] = (256, 256),
        seed: Optional[int] = None,
        map_path: Optional[str] = None,
    ):
        self.size = size
        self.seed = seed
        self.map_path = map_path
        self._loaded = False

        self.elevation = None
        self.temperature = None
        self.humidity = None
        self.pressure = None
        self.biome_map = None  # integer indices mapping to Biome

        # global atmospheric state (can be modified by biology over time)
        # start with very low O2: la complessità vegetale emergerà solo dopo
        self.global_o2 = 0.02
        self.global_co2 = 0.0004
        self.global_ch4 = 0.0

        # slow environmental memory fields (built from deaths, weathering, etc.)
        self.organic_layer = None
        self.mineral_layer = None

        # cells that require a local biome reclassification
        # (x, y) integer tile coordinates
        self._dirty_cells = set()

        self._generate_or_load()

    # --------------------------------------------------------
    # MAP GENERATION / LOADING
    # --------------------------------------------------------

    def _generate_or_load(self) -> None:
        gen = MapGenerator(size=self.size, seed=self.seed)
        data = gen.generate(save_path=self.map_path) if self.map_path else gen.generate()
        self.elevation = data["elevation"]
        self.temperature = data["temperature"]
        self.humidity = data["humidity"]
        self.pressure = data["pressure"]

        # prima classificazione globale (solo all'avvio)
        self._classify_biomes()

        # initialize slow fields with zeros
        h, w = self.elevation.shape
        self.organic_layer = np.zeros((h, w), dtype=np.float32)
        self.mineral_layer = np.zeros((h, w), dtype=np.float32)
        self._loaded = True

    # --------------------------------------------------------
    # BIOME CLASSIFICATION
    # --------------------------------------------------------

    def _local_noise_at(self, x: int, y: int) -> float:
        """Deterministic small-scale noise in [0,1] based on seed,x,y.
        Usato per frastagliare i biomi senza costose mappe extra.
        """
        base_seed = self.seed if self.seed is not None else 0
        v = (x * 73856093) ^ (y * 19349663) ^ (base_seed & 0xFFFFFFFF)
        v &= 0xFFFFFFFF
        if v == 0:
            return 0.0
        return v / 0xFFFFFFFF

    def _classify_biomes(self) -> None:
        """Classificazione completa di tutti i biomi.
        Usata solo all'avvio o in rari casi di reset globale.
        """
        h, w = self.elevation.shape
        self.biome_map = np.empty((h, w), dtype=np.uint8)
        mapping = {b: i for i, b in enumerate(Biome)}

        # primo passaggio: biomi base
        raw_biomes = np.empty((h, w), dtype=object)
        for y in range(h):
            for x in range(w):
                elev = float(self.elevation[y, x])
                temp = float(self.temperature[y, x])
                humid = float(self.humidity[y, x])
                pres = float(self.pressure[y, x])
                org = float(self.organic_layer[y, x]) if self.organic_layer is not None else 0.0
                miner = float(self.mineral_layer[y, x]) if self.mineral_layer is not None else 0.0
                b = biome_from_env(
                    elev,
                    temp,
                    humid,
                    pres,
                    global_o2=self.global_o2,
                    organic_layer=org,
                    mineral_layer=miner,
                    local_noise=self._local_noise_at(x, y),
                )
                raw_biomes[y, x] = b

        # secondo passaggio: inserisci fiumi e laghi interni basati su adiacenza
        for y in range(h):
            for x in range(w):
                b = raw_biomes[y, x]
                elev = float(self.elevation[y, x])
                humid = float(self.humidity[y, x])

                if b in (Biome.OCEAN, Biome.WATER, Biome.LAKE, Biome.RIVER, Biome.BEACH):
                    continue

                # finestra locale 3x3
                y0 = max(0, y - 1)
                y1 = min(h - 1, y + 1)
                x0 = max(0, x - 1)
                x1 = min(w - 1, x + 1)

                neighbors = {
                    raw_biomes[yy, xx]
                    for yy in range(y0, y1 + 1)
                    for xx in range(x0, x1 + 1)
                    if not (yy == y and xx == x)
                }

                # corsi d'acqua: altitudine medio-bassa, umidità alta, vicinanza a oceano/lago/river
                if 0.16 < elev < 0.65 and humid > 0.6:
                    if any(nb in (Biome.OCEAN, Biome.WATER, Biome.LAKE, Biome.BEACH, Biome.RIVER) for nb in neighbors):
                        raw_biomes[y, x] = Biome.RIVER
                        continue

                # laghi interni: tasche a bassa quota con umidità molto alta
                if elev < 0.32 and humid > 0.7:
                    if all(nb not in (Biome.OCEAN, Biome.WATER) for nb in neighbors):
                        raw_biomes[y, x] = Biome.LAKE

        # scrivi nella mappa finale
        for y in range(h):
            for x in range(w):
                self.biome_map[y, x] = mapping[raw_biomes[y, x]]

        # dopo una classificazione completa non ci sono celle sporche
        self._dirty_cells.clear()

    def _reclassify_cell(self, x: int, y: int) -> None:
        """Riclassifica solo la cella (x,y) in base allo stato corrente.

        Non ricrea i fiumi/lago globalmente; questo è sufficiente per
        aggiornare biomi che cambiano per effetto della biologia
        (accumulo di organico / variazione di gas).
        """
        h, w = self.elevation.shape
        if x < 0 or x >= w or y < 0 or y >= h:
            return

        elev = float(self.elevation[y, x])
        temp = float(self.temperature[y, x])
        humid = float(self.humidity[y, x])
        pres = float(self.pressure[y, x])
        org = float(self.organic_layer[y, x]) if self.organic_layer is not None else 0.0
        miner = float(self.mineral_layer[y, x]) if self.mineral_layer is not None else 0.0

        b = biome_from_env(
            elev,
            temp,
            humid,
            pres,
            global_o2=self.global_o2,
            organic_layer=org,
            mineral_layer=miner,
            local_noise=self._local_noise_at(x, y),
        )
        mapping = {b_enum: i for i, b_enum in enumerate(Biome)}
        self.biome_map[y, x] = mapping[b]

    # --------------------------------------------------------
    # BIOME ACCESSORS / RENDERING
    # --------------------------------------------------------

    def get_biome_at(self, x: int, y: int) -> Biome:
        """Return Biome enum at tile coordinates (x,y)."""
        h, w = self.biome_map.shape
        if x < 0 or x >= w or y < 0 or y >= h:
            return Biome.OCEAN
        idx = int(self.biome_map[y, x])
        return list(Biome)[idx]

    def color_map(self) -> np.ndarray:
        """Return an (h,w,3) uint8 color image of the biome map for rendering.
        Apply subtle shading based on elevation and temperature so biomes
        have gentle internal variation.
        """
        h, w = self.biome_map.shape
        img = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                b = self.get_biome_at(x, y)
                base = np.array(color_for_biome(b), dtype=np.float32)
                elev = float(self.elevation[y, x])
                temp = float(self.temperature[y, x])
                # Elevation: higher = slightly brighter
                light_factor = 0.75 + 0.35 * elev
                # Temperature tint: warm -> more red, cold -> more blue
                warm_cold = (temp - 0.5) * 0.3
                tint = np.array([40.0, 10.0, -30.0]) * warm_cold
                color = base * light_factor + tint
                color = np.clip(color, 0.0, 255.0)
                img[y, x] = color.astype(np.uint8)
        return img

    def save_snapshot(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(
            path,
            elevation=self.elevation,
            temperature=self.temperature,
            humidity=self.humidity,
            pressure=self.pressure,
            biome=self.biome_map,
        )

    def load_snapshot(self, path: str) -> None:
        data = np.load(path)
        self.elevation = data["elevation"]
        self.temperature = data["temperature"]
        self.humidity = data["humidity"]
        self.pressure = data["pressure"]
        self.biome_map = data.get("biome")
        # re-create environmental memory fields if missing
        h, w = self.elevation.shape
        if self.organic_layer is None or self.organic_layer.shape != (h, w):
            self.organic_layer = np.zeros((h, w), dtype=np.float32)
        if self.mineral_layer is None or self.mineral_layer.shape != (h, w):
            self.mineral_layer = np.zeros((h, w), dtype=np.float32)
        self._loaded = True

    # --------------------------------------------------------
    # ENVIRONMENTAL INPUTS
    # --------------------------------------------------------

    def get_environment_inputs(self, x: int, y: int, t: float) -> Dict[str, float]:
        """Return raw environmental inputs at tile (x,y) for time t.
        Values are in the channels defined by ENV_CHANNELS.
        """
        b = self.get_biome_at(x, y)
        lat_frac = float(self.pressure[y, x]) if self.pressure is not None else 0.5
        env = sample_environment(b, lat_frac, t)

        # ORGANIC_SOUP è modulato dallo strato organico locale:
        # nelle fasi primordiali (organic_layer ~ 0) non esistono
        # organici ambientali, ma solo ciò che rilasciano i pixel.
        if "ORGANIC_SOUP" in env and self.organic_layer is not None:
            org = float(self.organic_layer[y, x])
            # semplice mappatura saturante: pochi organici -> quasi zero soup
            factor = max(0.0, min(1.0, org * 0.1))
            env["ORGANIC_SOUP"] *= factor

        return env

    # --------------------------------------------------------
    # SLOW ENVIRONMENTAL DYNAMICS (TIME-DEPENDENT)
    # --------------------------------------------------------

    def advance_environment(self, dt: float) -> None:
        """Advance slow environmental fields (organic/mineral layers, gases)
        and re-classify biomes only where the environment has really changed.
        """
        if self.organic_layer is not None:
            # very slow decay of organic matter
            decay_o = 1.0 - min(0.0001 * dt, 0.05)
            self.organic_layer *= decay_o
        if self.mineral_layer is not None:
            # minerals decay / diffuse even più lentamente
            decay_m = 1.0 - min(0.00002 * dt, 0.02)
            self.mineral_layer *= decay_m

        # relax global gases slowly towards baseline if biology isn't pushing them
        base_o2 = 0.02
        base_co2 = 0.0004
        relax = min(0.00005 * dt, 0.01)
        self.global_o2 += (base_o2 - self.global_o2) * relax
        self.global_co2 += (base_co2 - self.global_co2) * relax
        # methane naturally tende a zero in assenza di sorgenti
        self.global_ch4 += (0.0 - self.global_ch4) * relax

        # riclassifica solo le celle segnate come "sporche" da eventi
        # biologici (es. morte dei pixel) per evitare grossi spike di calcolo
        if self._dirty_cells:
            max_per_step = min(512, len(self._dirty_cells))
            for _ in range(max_per_step):
                x, y = self._dirty_cells.pop()
                self._reclassify_cell(x, y)

    def deposit_biomass(self, x: int, y: int, organics: float, minerals: float) -> None:
        """Deposit organic/mineral matter at tile (x,y) when cells die.

        Questo è il gancio che collega direttamente biologia e biomi:
        appena si accumula biomassa, marchiamo la cella (e i vicini) come
        "sporchi" così verranno riclassificati gradualmente nei tick
        successivi da advance_environment.
        """
        if self.organic_layer is None or self.mineral_layer is None:
            return
        h, w = self.organic_layer.shape
        if x < 0 or x >= w or y < 0 or y >= h:
            return

        self.organic_layer[y, x] += float(max(0.0, organics))
        self.mineral_layer[y, x] += float(max(0.0, minerals))

        # marca la cella e il suo intorno 3x3 come "sporchi"
        for yy in range(max(0, y - 1), min(h, y + 2)):
            for xx in range(max(0, x - 1), min(w, x + 2)):
                self._dirty_cells.add((xx, yy))


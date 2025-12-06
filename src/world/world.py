# --------------------------------------------------------
# File: src/world/world.py
"""
World object: coordinates the map fields, biome classification and resource grid.
"""
from typing import Optional, Tuple, Dict
import numpy as np
import os

from .map_generator import MapGenerator
from .biome import biome_from_env, Biome, color_for_biome
from .environment import sample_environment, ENV_CHANNELS


class World:
    def __init__(self, size: Tuple[int, int] = (256, 256), seed: Optional[int] = None, map_path: Optional[str] = None):
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
        # start with very low O2: complessità vegetale emergerà solo dopo
        self.global_o2 = 0.02
        self.global_co2 = 0.0004
        self.global_ch4 = 0.0
        # slow environmental memory fields (built from deaths, weathering, etc.)
        self.organic_layer = None
        self.mineral_layer = None
        self._generate_or_load()

    def _generate_or_load(self):
        gen = MapGenerator(size=self.size, seed=self.seed)
        data = gen.generate(save_path=self.map_path) if self.map_path else gen.generate()
        self.elevation = data["elevation"]
        self.temperature = data["temperature"]
        self.humidity = data["humidity"]
        self.pressure = data["pressure"]
        self._classify_biomes()
        # initialize slow fields with zeros
        h, w = self.elevation.shape
        self.organic_layer = np.zeros((h, w), dtype=np.float32)
        self.mineral_layer = np.zeros((h, w), dtype=np.float32)
        self._loaded = True

    def _classify_biomes(self):
        h, w = self.elevation.shape
        self.biome_map = np.empty((h, w), dtype=np.uint8)
        # map Biome values to small ints
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

                neighbors = {raw_biomes[yy, xx] for yy in range(y0, y1 + 1) for xx in range(x0, x1 + 1) if not (yy == y and xx == x)}

                # corsi d'acqua: altitudine medio-bassa, umidità alta, vicinanza a oceano/lago/river
                if 0.18 < elev < 0.55 and humid > 0.7:
                    if any(nb in (Biome.OCEAN, Biome.WATER, Biome.LAKE, Biome.BEACH, Biome.RIVER) for nb in neighbors):
                        raw_biomes[y, x] = Biome.RIVER
                        continue

                # laghi interni: tasche a bassa quota con umidità molto alta
                if elev < 0.30 and humid > 0.8:
                    if all(nb not in (Biome.OCEAN, Biome.WATER) for nb in neighbors):
                        raw_biomes[y, x] = Biome.LAKE

        # scrivi nella mappa finale
        for y in range(h):
            for x in range(w):
                self.biome_map[y, x] = mapping[raw_biomes[y, x]]

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

    def save_snapshot(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path, elevation=self.elevation, temperature=self.temperature, humidity=self.humidity, pressure=self.pressure, biome=self.biome_map)

    def load_snapshot(self, path: str):
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
        return sample_environment(b, lat_frac, t)

    # --------------------------------------------------------
    # SLOW ENVIRONMENTAL DYNAMICS (TIME-DEPENDENT)
    # --------------------------------------------------------

    def advance_environment(self, dt: float):
        """Advance slow environmental fields (organic/mineral layers, gases)
        and slowly re-classify biomes as biology modifica il suolo/atmosfera.
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

        # accumula tempo e ogni tanto riclassifica i biomi usando i nuovi
        # strati organici/minerali e lo stato atmosferico globale
        t = getattr(self, "_biome_reclass_timer", 0.0) + dt
        # scala di tempo volutamente lunga per simulare "epoche"
        if t >= 50.0:
            self._classify_biomes()
            # segnala agli eventuali renderer che la mappa biomi è cambiata
            setattr(self, "_biome_dirty", True)
            t = 0.0
        self._biome_reclass_timer = t

    def deposit_biomass(self, x: int, y: int, organics: float, minerals: float):
        """Deposit organic/mineral matter at tile (x,y) when cells die."""
        if self.organic_layer is None or self.mineral_layer is None:
            return
        h, w = self.organic_layer.shape
        if x < 0 or x >= w or y < 0 or y >= h:
            return
        self.organic_layer[y, x] += float(max(0.0, organics))
        self.mineral_layer[y, x] += float(max(0.0, minerals))

# -------------------------------------------------
# src/pixel/pixel_manager.py
"""
PixelManager: gestisce un insieme di "pixel" biologici in modo
data‑oriented. È pensato per essere semplice da leggere ed estendere.

Punti chiave rispetto al modello evolutivo che vogliamo:

- Tutte le unità iniziali sono quasi identiche e *prive* di tratti
  avanzati: nessuna motilità attiva, nessuna capacità di replicazione
  affidabile garantita.
- La motilità è un *tratto genetico*: senza un gene di motilità sopra
  soglia, il movimento è quasi nullo e puramente passivo (vento/jitter).
- La riproduzione 1→2 è costosa e opzionale: richiede sia un gene di
  replicazione sia scorte interne sufficienti, con mutazioni sul genoma.
"""
from typing import List, Tuple, Optional, Dict
import importlib
import importlib.util
import math

import numpy as np

from .pixel import Pixel
from world.biome import Biome


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


class PixelManager:
    def __init__(self, capacity: int = 1024):
        # storage di base
        self.capacity = capacity
        self.count = 0
        self.positions = np.zeros((capacity, 2), dtype=np.float32)
        self.energies = np.ones((capacity,), dtype=np.float32)
        self.stamina = np.ones((capacity,), dtype=np.float32)
        self.alive = np.ones((capacity,), dtype=np.bool_)
        self.time = 0.0

        # birth timestamps (in simulation time) per età di linea
        self.birth_time = np.zeros((capacity,), dtype=np.float32)
        # storia energetica lenta per segnali di omeostasi
        self._energy_avg = np.ones((capacity,), dtype=np.float32)
        self._energy_var = np.zeros((capacity,), dtype=np.float32)

        # identità di "specie" emergente (inizialmente tutte uguali)
        self.species: List[str] = ["proto"] * capacity

        # moduli opzionali
        self.genomes: List[Optional[object]] = [None] * capacity
        # tratti evolutivi decodificati dal genoma (skill attive)
        self.traits: List[set] = [set() for _ in range(capacity)]
        self.internal_resources = None

        self.has_genome = _module_exists("pixel.genome")
        self.has_metabolism = _module_exists("pixel.metabolism")
        self.has_reproduction = _module_exists("pixel.reproduction")

        if not (self.has_genome and self.has_metabolism and self.has_reproduction):
            print(
                "[pixel_manager] Attenzione: moduli opzionali mancanti. "
                f"(genome={self.has_genome}, metabolism={self.has_metabolism}, "
                f"reproduction={self.has_reproduction})"
            )

        # lazy imports
        self._genome_mod = importlib.import_module("pixel.genome") if self.has_genome else None
        self._metabolism_mod = importlib.import_module("pixel.metabolism") if self.has_metabolism else None
        self._reproduction_mod = importlib.import_module("pixel.reproduction") if self.has_reproduction else None

        if self._metabolism_mod is not None:
            try:
                self.internal_resources = self._metabolism_mod.init_internal_state(self.capacity)
            except Exception:
                self.internal_resources = None

    # ------------------------------------------------------------------
    # GENOME / TRAITS
    # ------------------------------------------------------------------

    def _motility_level(self, idx: int) -> int:
        """
        Livelli di motilità:
          0 = nessuna motilità (unità quasi immobile, solo vento/jitter minimo)
          1 = motilità primitiva (random walk lento)
          2 = motilità direzionale (può usare decide_move verso nutrienti)

        Il livello è derivato da un gene numerico nel genoma.
        """
        if not self.has_genome or self._genome_mod is None:
            return 0
        if idx >= len(self.genomes):
            return 0
        g = getattr(self.genomes[idx], "data", None)
        if g is None:
            return 0
        try:
            arr = np.asarray(g, dtype=float).ravel()
            if arr.size < 2:
                return 0
            mot = float(arr[1])
        except Exception:
            return 0

        level = 0
        if mot >= 0.2:
            level = 1
        if mot >= 0.6:
            level = 2

        # upgrade basato sui tratti evolutivi (skill):
        # - cilia / flagella -> almeno livello 1
        # - muscle / legs / fins / wings -> almeno livello 2
        traits = self.traits[idx] if idx < len(self.traits) else set()
        if any(t in traits for t in ("cilia", "flagella")):
            level = max(level, 1)
        if any(t in traits for t in ("muscle", "legs", "fins", "wings")):
            level = max(level, 2)

        return level

    # ------------------------------------------------------------------
    # SPAWN
    # ------------------------------------------------------------------

    def spawn_random(self, world, resource_grid=None, n: int = 100, species_prefix: str = "Spec") -> List[int]:
        """Spawn iniziale dei pixel.

        Tutti gli individui nascono in una singola regione locale, scelta
        casualmente ma *in prossimità dell'acqua* (oceano/costa/lago/fiume).
        Questo rappresenta un "luogo di origine" per run e rende più
        probabile l'emergere di una linea evolutiva, mantenendo però
        casuale dove avviene.
        """
        ids: List[int] = []
        h, w = world.size[1], world.size[0]

        # scegli un solo centro casuale MA vicino all'acqua
        water_biomes = {Biome.OCEAN, Biome.WATER, Biome.LAKE, Biome.RIVER}
        beach_like = {Biome.BEACH, Biome.MANGROVE, Biome.SWAMP}
        rng = np.random.default_rng()
        cx, cy = None, None
        for _ in range(2000):
            tx = rng.integers(0, w)
            ty = rng.integers(0, h)
            b = world.get_biome_at(int(tx), int(ty))
            if b in water_biomes or b in beach_like:
                cx, cy = float(tx), float(ty)
                break
        if cx is None or cy is None:
            # fallback: centro puramente casuale
            cx = np.random.rand() * (w - 1)
            cy = np.random.rand() * (h - 1)
        # raggio locale (in tile) intorno al centro
        sigma = max(2.0, min(w, h) * 0.02)  # ~2% della dimensione come deviazione

        for _ in range(n):
            if self.count >= self.capacity:
                break
            idx = self.count

            # spawn in un intorno gaussiano del centro
            x = np.random.normal(cx, sigma)
            y = np.random.normal(cy, sigma)
            # clamp ai bordi del mondo
            x = max(0.0, min(float(w - 1), x))
            y = max(0.0, min(float(h - 1), y))

            self.positions[idx, 0] = x
            self.positions[idx, 1] = y
            self.energies[idx] = 1.0
            self.stamina[idx] = 1.0
            self.alive[idx] = True
            self.birth_time[idx] = float(self.time)
            self.species[idx] = "proto"

            if self.has_genome and self._genome_mod is not None:
                try:
                    genome_obj = self._genome_mod.random_genome()
                    self.genomes[idx] = genome_obj
                    # decodifica tratti come skill iniziali (di fatto quasi vuoti)
                    try:
                        from .genome import decode_traits

                        self.traits[idx] = decode_traits(genome_obj)
                    except Exception:
                        self.traits[idx] = set()
                except Exception:
                    self.genomes[idx] = None
                    self.traits[idx] = set()

            if self.internal_resources is not None and self._metabolism_mod is not None:
                try:
                    self.internal_resources[idx, :] = self._metabolism_mod.init_internal_state(1)[0]
                except Exception:
                    pass

            ids.append(idx)
            self.count += 1
        return ids

    # ------------------------------------------------------------------
    # MAIN STEP
    # ------------------------------------------------------------------

    def step(self, dt: float, world, resource_grid=None):
        """Advance simulation by dt (o tick) lato fisico/biologico."""
        self.time += dt

        # processi ambientali lenti
        advance_env = getattr(world, "advance_environment", None)
        if callable(advance_env):
            advance_env(dt)

        for i in range(self.count):
            if not self.alive[i]:
                continue

            x = float(self.positions[i, 0])
            y = float(self.positions[i, 1])
            e = float(self.energies[i])

            # aggiornamento statistica energetica
            avg = float(self._energy_avg[i])
            var = float(self._energy_var[i])
            alpha = 0.01
            new_avg = (1.0 - alpha) * avg + alpha * e
            new_var = (1.0 - alpha) * var + alpha * (e - avg) ** 2
            self._energy_avg[i] = new_avg
            self._energy_var[i] = new_var

            # segnali fisici (no antropomorfismo)
            energy_deficit_signal = max(0.0, 0.5 - e)
            homeostasis_error = new_var
            metabolic_stress = energy_deficit_signal + homeostasis_error

            mot_level = self._motility_level(i)

            # ------------------ MOVIMENTO + NUTRIMENTO -------------------
            if e < 0.4:
                eaten = False
                if resource_grid is not None:
                    tx, ty = int(round(x)), int(round(y))
                    atom_list = getattr(resource_grid, "atom_types", None)
                    try:
                        from world.resources import ATOM_TYPES as GLOBAL_ATOMS
                        atom_list = GLOBAL_ATOMS
                    except Exception:
                        atom_list = getattr(resource_grid, "ATOM_TYPES", None)

                    if atom_list is None:
                        if resource_grid.consume_atom(tx, ty, 0, amount=1):
                            self.energies[i] = min(1.0, e + 0.05)
                            eaten = True
                    else:
                        best_gain = -999.0
                        best_j: Optional[int] = None
                        for j, atom_symbol in enumerate(atom_list):
                            gain = 0.0
                            if self.has_metabolism and self._metabolism_mod is not None:
                                try:
                                    gain = self._metabolism_mod.nutrient_to_energy(atom_symbol)
                                except Exception:
                                    gain = 0.0
                            else:
                                if atom_symbol == "P":
                                    gain = 0.05
                                elif atom_symbol == "X":
                                    gain = -0.2
                                elif atom_symbol == "Cl":
                                    gain = -0.02
                            if gain > best_gain:
                                best_gain = gain
                                best_j = j
                        if best_j is not None and resource_grid.consume_atom(tx, ty, best_j, amount=1):
                            self.energies[i] = float(min(1.0, e + max(0.0, best_gain)))
                            eaten = True

                if not eaten:
                    # fame ma nessun cibo: movimento dipende dal livello di motilità
                    if mot_level == 0:
                        speed = 0.01  # quasi immobile: solo vento/jitter minimo
                    elif mot_level == 1:
                        speed = 0.15
                    else:
                        speed = 0.8
                    nx, ny = self._random_walk(x, y, speed * dt)
                    self.positions[i, 0] = nx
                    self.positions[i, 1] = ny

            else:
                # energia sufficiente
                if mot_level == 0:
                    # nessuna motilità: resta quasi ferma, anche se sotto stress
                    base_speed = 0.01 + 0.04 * min(1.0, metabolic_stress)
                    nx, ny = self._random_walk(x, y, base_speed * dt)
                elif mot_level == 1:
                    # motilità primitiva: random walk moderato, niente decide_move
                    base_speed = 0.05 + 0.2 * min(1.0, metabolic_stress)
                    nx, ny = self._random_walk(x, y, base_speed * dt)
                else:
                    # motilità avanzata: cerca nutrienti quando stressato
                    if metabolic_stress < 0.05:
                        nx, ny = self._random_walk(x, y, 0.1 * dt)
                    else:
                        try:
                            from pixel.behaviors import decide_move

                            nx, ny = decide_move(x, y, world, resource_grid, perception=3)
                        except Exception:
                            nx, ny = self._random_walk(x, y, 0.3 * dt)
                self.positions[i, 0] = nx
                self.positions[i, 1] = ny

            # ------------------ METABOLISMO -------------------
            if self.has_metabolism and self._metabolism_mod is not None:
                try:
                    tx, ty = int(round(x)), int(round(y))
                    env_inputs: Dict[str, float] = {}
                    get_env = getattr(world, "get_environment_inputs", None)
                    if callable(get_env):
                        env_inputs = get_env(tx, ty, self.time)
                    self._metabolism_mod.step_pixel_metabolism(self, i, env_inputs or {}, dt)
                except Exception:
                    self.energies[i] = float(self.energies[i] - 0.001 * dt)
            else:
                self.energies[i] = float(self.energies[i] - 0.001 * dt)

            # ------------------ CLAMP & MORTE -------------------
            self._clamp(i, world)
            if self.energies[i] <= 0.0:
                if self.internal_resources is not None:
                    try:
                        tx, ty = int(round(self.positions[i, 0])), int(round(self.positions[i, 1]))
                        organics = float(self.internal_resources[i, 1])
                        minerals = float(self.internal_resources[i, 2])
                        if hasattr(world, "deposit_biomass"):
                            world.deposit_biomass(tx, ty, organics, minerals)
                    except Exception:
                        pass
                self.alive[i] = False

        # riproduzione asessuata 1->2
        if self.has_reproduction and self._reproduction_mod is not None:
            self._attempt_asexual_division(world)

    # ------------------------------------------------------------------
    # RIPRODUZIONE
    # ------------------------------------------------------------------

    def _spawn_child(self, x: float, y: float, genome_obj, species_name: str) -> Optional[int]:
        if self.count >= self.capacity:
            return None
        idx = self.count
        self.positions[idx, 0] = x
        self.positions[idx, 1] = y
        self.energies[idx] = 0.8
        self.stamina[idx] = 0.8
        self.alive[idx] = True
        self.species[idx] = species_name
        self.genomes[idx] = genome_obj
        self.birth_time[idx] = float(self.time)
        if self.internal_resources is not None and self._metabolism_mod is not None:
            try:
                self.internal_resources[idx, :] = self._metabolism_mod.init_internal_state(1)[0]
            except Exception:
                pass
        self.count += 1
        return idx

    def _attempt_asexual_division(self, world):
        """
        Asexual 1 -> 2 divisione basata su:
          - gene di replicazione
          - scorte interne minime
          - stress metabolico (troppo basso o troppo alto → niente divisione)
        """
        if self.internal_resources is None or self._metabolism_mod is None:
            return

        sm = self._metabolism_mod
        idx_e = sm.IDX_ENERGY
        idx_o = sm.IDX_ORGANICS
        idx_m = sm.IDX_MEMBRANE
        idx_info = sm.IDX_INFO

        for i in range(self.count):
            if not self.alive[i]:
                continue
            genome_obj = self.genomes[i]
            if genome_obj is None or self._reproduction_mod is None:
                continue

            try:
                if not self._reproduction_mod.has_basic_replication(genome_obj):
                    continue
            except Exception:
                continue

            stocks = self.internal_resources[i]
            try:
                ok = self._reproduction_mod.division_conditions_met(stocks, idx_e, idx_o, idx_m, idx_info)
            except Exception:
                ok = False
            if not ok:
                continue

            # stress metabolico controlla la probabilità / mutazione
            e = float(stocks[idx_e])
            avg = float(self._energy_avg[i])
            var = float(self._energy_var[i])
            energy_deficit_signal = max(0.0, 0.5 - e)
            homeostasis_error = var
            metabolic_stress = energy_deficit_signal + homeostasis_error

            if metabolic_stress < 0.02:
                continue

            from pixel.genome import Genome

            try:
                base = np.asarray(genome_obj.data, dtype=float)
                sigma = 0.003 + min(0.03, metabolic_stress * 0.1)
                mutated = base + np.random.normal(scale=sigma, size=base.shape)
                child_genome = Genome(data=mutated)
            except Exception:
                child_genome = genome_obj

            cx = float(self.positions[i, 0]) + (np.random.rand() - 0.5) * 0.5
            cy = float(self.positions[i, 1]) + (np.random.rand() - 0.5) * 0.5
            child_idx = self._spawn_child(cx, cy, child_genome, self.species[i])
            if child_idx is None:
                continue

            # aggiorna anche i tratti del figlio (skill)
            try:
                from .genome import decode_traits

                self.traits[child_idx] = decode_traits(child_genome)
            except Exception:
                self.traits[child_idx] = set()

            child_stocks = self.internal_resources[child_idx]
            child_stocks[:] = stocks * 0.4
            stocks[:] *= 0.4

            stocks[idx_e] *= 0.8
            child_stocks[idx_e] *= 0.8

    # ------------------------------------------------------------------
    # UTILITY
    # ------------------------------------------------------------------

    def _random_walk(self, x: float, y: float, speed: float = 1.0) -> Tuple[float, float]:
        nx = x + (np.random.rand() - 0.5) * 2.0 * speed
        ny = y + (np.random.rand() - 0.5) * 2.0 * speed
        return nx, ny

    def _clamp(self, idx: int, world):
        w, h = world.size
        x = float(self.positions[idx, 0])
        y = float(self.positions[idx, 1])
        x = max(0.0, min(float(w - 1), x))
        y = max(0.0, min(float(h - 1), y))
        self.positions[idx, 0] = x
        self.positions[idx, 1] = y

    # small helpers used by other parts of the codebase

    def get_pixel_info(self, idx: int) -> dict:
        if idx < 0 or idx >= self.count:
            return {}
        return {
            "id": idx,
            "species": self.species[idx],
            "x": float(self.positions[idx, 0]),
            "y": float(self.positions[idx, 1]),
            "energy": float(self.energies[idx]),
            "alive": bool(self.alive[idx]),
        }

    def find_nearest(self, x: float, y: float, radius: float = 2.0) -> Optional[int]:
        best = None
        bestd = radius
        for i in range(self.count):
            if not self.alive[i]:
                continue
            dx = float(self.positions[i, 0]) - x
            dy = float(self.positions[i, 1]) - y
            d = math.hypot(dx, dy)
            if d < bestd:
                bestd = d
                best = i
        return best

    def to_list(self) -> List[dict]:
        return [self.get_pixel_info(i) for i in range(self.count)]

    def save(self, path: str):
        import os

        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(
            path,
            positions=self.positions[: self.count],
            energies=self.energies[: self.count],
            species=self.species[: self.count],
        )

    def load(self, path: str):
        data = np.load(path, allow_pickle=True)
        pos = data["positions"]
        n = pos.shape[0]
        self.count = min(n, self.capacity)
        self.positions[: self.count] = pos[: self.count]
        self.energies[: self.count] = data["energies"][: self.count]
        sp = data["species"][: self.count]
        for i in range(self.count):
            self.species[i] = str(sp[i])

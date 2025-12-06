# -------------------------------------------------
# src/pixel/pixel_manager.py
"""
PixelManager: manages a collection of Pixels in a data-oriented way.
It is tolerant to missing modules (genome, metabolism, reproduction).
If those modules are not present, the manager will operate with
fallback behaviours and print a warning message.

Responsibilities:
- spawn pixels randomly on a provided World
- vectorized-ish storage for positions and energies
- per-tick update: movement, feeding when energy < 0.4
- simple mating attempt when two pixels of high similarity are nearby

This manager is intentionally simple and clear; later it can be
optimized with NumPy arrays + numba for heavy simulations.
"""
from typing import List, Tuple, Optional
import importlib
import importlib.util
import numpy as np
import math

from .pixel import Pixel


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


class PixelManager:
    def __init__(self, capacity: int = 1024):
        # storage
        self.capacity = capacity
        self.count = 0
        self.positions = np.zeros((capacity, 2), dtype=np.float32)
        self.energies = np.ones((capacity,), dtype=np.float32)
        self.stamina = np.ones((capacity,), dtype=np.float32)
        self.alive = np.ones((capacity,), dtype=np.bool_)
        self.time = 0.0
        # birth timestamps (in simulation time) for lineage age
        self.birth_time = np.zeros((capacity,), dtype=np.float32)
        # simple internal state history for "comfort" vs "distress"
        self._energy_avg = np.ones((capacity,), dtype=np.float32)
        self._energy_var = np.zeros((capacity,), dtype=np.float32)
        # species names (conceptually: emergent identity; start as undifferentiated)
        self.species: List[str] = ["proto"] * capacity
        # optional genomes storage (only if genome module available)
        self.genomes = [None] * capacity
        # optional internal resource stocks (filled when metabolism is available)
        self.internal_resources = None

        # detection of optional modules
        self.has_genome = _module_exists("pixel.genome")
        self.has_metabolism = _module_exists("pixel.metabolism")
        self.has_reproduction = _module_exists("pixel.reproduction")

        if not (self.has_genome and self.has_metabolism and self.has_reproduction):
            print("[pixel_manager] Attenzione: moduli opzionali mancanti. I pixel non sanno cosa fare completamente. (genome={}, metabolism={}, reproduction={})".format(self.has_genome, self.has_metabolism, self.has_reproduction))

        # lazy imports
        self._genome_mod = None
        self._metabolism_mod = None
        self._reproduction_mod = None
        if self.has_genome:
            self._genome_mod = importlib.import_module("pixel.genome")
        if self.has_metabolism:
            self._metabolism_mod = importlib.import_module("pixel.metabolism")
            try:
                # allocate internal resource stocks if helper provided
                self.internal_resources = self._metabolism_mod.init_internal_state(self.capacity)
            except Exception:
                self.internal_resources = None
        if self.has_reproduction:
            self._reproduction_mod = importlib.import_module("pixel.reproduction")
        # simple global "wind" vector for passive drift (world units per tick)
        self._wind_dx = 0.0
        self._wind_dy = 0.0

    # -----------------------------
    # MOTILITY HELPERS
    # -----------------------------

    def _has_active_motility(self, idx: int) -> bool:
        """Return True if this pixel has evolved active motility.

        For now we approximate this by checking a dedicated gene slot in the
        numeric genome vector. Early pixels will typically not meet the
        threshold, so they only experience tiny random drift (or wind).
        """
        if not (self.has_genome and self._genome_mod is not None):
            return False
        if idx >= len(self.genomes):
            return False
        g = getattr(self.genomes[idx], "data", None)
        if g is None:
            return False
        try:
            arr = np.asarray(g, dtype=float).ravel()
            if arr.size < 2:
                return False
            motility_gene = float(arr[1])
            return motility_gene >= 0.7
        except Exception:
            return False

    def spawn_random(self, world, resource_grid=None, n: int = 100, species_prefix: str = "Spec") -> List[int]:
        ids = []
        h, w = world.size[1], world.size[0]
        for i in range(n):
            if self.count >= self.capacity:
                break
            x = np.random.rand() * (w - 1)
            y = np.random.rand() * (h - 1)
            idx = self.count
            self.positions[idx, 0] = x
            self.positions[idx, 1] = y
            self.energies[idx] = 1.0
            self.stamina[idx] = 1.0
            self.alive[idx] = True
            self.birth_time[idx] = float(self.time)
            # inizialmente tutte le entità sono indifferenziate: nessuna specie distinta
            self.species[idx] = "proto"
            # if genome module available, assign random genome
            if self.has_genome and self._genome_mod is not None:
                try:
                    self.genomes[idx] = self._genome_mod.random_genome()
                except Exception:
                    self.genomes[idx] = None
            # initialize internal resources for this pixel if available
            if self.internal_resources is not None and self._metabolism_mod is not None:
                try:
                    # reuse init helper for a single row default
                    self.internal_resources[idx, :] = self._metabolism_mod.init_internal_state(1)[0]
                except Exception:
                    pass
            ids.append(idx)
            self.count += 1
        return ids

    def step(self, dt: float, world, resource_grid=None):
        """Advance simulation by dt seconds (or ticks)."""
        self.time += dt
        # advance slow environmental processes (organic layers, gases)
        advance_env = getattr(world, "advance_environment", None)
        if callable(advance_env):
            advance_env(dt)
        # simple loop for clarity (vectorization later)
        for i in range(self.count):
            if not self.alive[i]:
                continue
            x, y = float(self.positions[i, 0]), float(self.positions[i, 1])
            e = float(self.energies[i])

            # aggiornamento semplice della statistica energetica per errori di omeostasi
            avg = float(self._energy_avg[i])
            var = float(self._energy_var[i])
            alpha = 0.01
            new_avg = (1.0 - alpha) * avg + alpha * e
            new_var = (1.0 - alpha) * var + alpha * (e - avg) ** 2
            self._energy_avg[i] = new_avg
            self._energy_var[i] = new_var

            # segnali interni in termini fisici, non antropomorfici
            energy_deficit_signal = max(0.0, 0.5 - e)
            homeostasis_error = new_var
            metabolic_stress = energy_deficit_signal + homeostasis_error

            # decide action: omeostasi = quasi fermo, stress = esplorazione / tentativi
            if e < 0.4:
                # forte deficit: prova prima a nutrirsi, altrimenti esplora
                eaten = False
                if resource_grid is not None:
                    tx, ty = int(round(x)), int(round(y))
                    # use the public ATOM_TYPES list if present
                    atom_list = getattr(resource_grid, 'atom_types', None)
                    # our resources module exposes ATOM_TYPES at module level; try fallback
                    try:
                        from world.resources import ATOM_TYPES as GLOBAL_ATOMS
                        atom_list = GLOBAL_ATOMS
                    except Exception:
                        atom_list = getattr(resource_grid, 'ATOM_TYPES', None)

                    if atom_list is None:
                        if resource_grid.consume_atom(tx, ty, 0, amount=1):
                            self.energies[i] = min(1.0, e + 0.05)
                            eaten = True
                    else:
                        best_gain = -999.0
                        best_j = None
                        for j, atom_symbol in enumerate(atom_list):
                            gain = 0.0
                            if self.has_metabolism and self._metabolism_mod is not None:
                                try:
                                    gain = self._metabolism_mod.nutrient_to_energy(atom_symbol)
                                except Exception:
                                    gain = 0.0
                            else:
                                if atom_symbol == 'P':
                                    gain = 0.05
                                elif atom_symbol == 'X':
                                    gain = -0.2
                                elif atom_symbol == 'Cl':
                                    gain = -0.02
                            if gain > best_gain:
                                best_gain = gain
                                best_j = j
                        if best_j is not None and resource_grid.consume_atom(tx, ty, best_j, amount=1):
                            self.energies[i] = float(min(1.0, e + max(0.0, best_gain)))
                            eaten = True
                if not eaten:
                    # non trova nutrimento: esplorazione più ampia
                    nx, ny = self._random_walk(x, y, speed=1.5)
                    self.positions[i, 0] = nx
                    self.positions[i, 1] = ny
            else:
                # energia sufficiente: se metabolic_stress basso resta quasi ferma, se alto esplora
                if metabolic_stress < 0.05:
                    nx, ny = self._random_walk(x, y, speed=0.2)
                else:
                    try:
                        from pixel.behaviors import decide_move
                        nx, ny = decide_move(x, y, world, resource_grid, perception=3)
                    except Exception:
                        nx, ny = self._random_walk(x, y, speed=1.0)
                self.positions[i, 0] = nx
                self.positions[i, 1] = ny

            # metabolism: convert environment -> internal resources
            if self.has_metabolism and self._metabolism_mod is not None:
                try:
                    tx, ty = int(round(x)), int(round(y))
                    env_inputs = {}
                    # World may expose get_environment_inputs, otherwise keep empty
                    get_env = getattr(world, "get_environment_inputs", None)
                    if callable(get_env):
                        env_inputs = get_env(tx, ty, self.time)
                    self._metabolism_mod.step_pixel_metabolism(self, i, env_inputs or {}, dt)
                except Exception:
                    # fallback simple cost
                    self.energies[i] = float(self.energies[i] - 0.001 * dt)
            else:
                self.energies[i] = float(self.energies[i] - 0.001 * dt)

            # clamp and death
            self._clamp(i, world)
            if self.energies[i] <= 0.0:
                # deposit biomass into the world when a pixel dies
                if self.internal_resources is not None:
                    try:
                        tx, ty = int(round(self.positions[i, 0])), int(round(self.positions[i, 1]))
                        organics = float(self.internal_resources[i, 1])  # IDX_ORGANICS
                        minerals = float(self.internal_resources[i, 2])  # IDX_MINERALS
                        if hasattr(world, "deposit_biomass"):
                            world.deposit_biomass(tx, ty, organics, minerals)
                    except Exception:
                        pass
                self.alive[i] = False

        # after movement, attempt asexual reproduction (1 -> 2) only
        if self.has_reproduction and self._reproduction_mod is not None:
            self._attempt_asexual_division(world)

    def _attempt_reproduction(self, world):
        # naive O(n^2) neighbor check for simplicity; will be replaced by spatial hash.
        threshold = 0.9
        for i in range(self.count):
            if not self.alive[i]:
                continue
            for j in range(i + 1, self.count):
                if not self.alive[j]:
                    continue
                # proximity
                dx = float(self.positions[i, 0]) - float(self.positions[j, 0])
                dy = float(self.positions[i, 1]) - float(self.positions[j, 1])
                dist = math.hypot(dx, dy)
                if dist > 2.0:
                    continue
                # compute similarity
                sim = 0.0
                if self.has_genome and self._genome_mod is not None and self.genomes[i] is not None and self.genomes[j] is not None:
                    try:
                        sim = float(self._genome_mod.similarity(self.genomes[i], self.genomes[j]))
                    except Exception:
                        sim = 0.0
                else:
                    # fallback: same species name considered similar
                    sim = 1.0 if self.species[i] == self.species[j] else 0.0

                if self._reproduction_mod and self._reproduction_mod.can_reproduce(sim, threshold):
                    try:
                        child_genome, child_species = self._reproduction_mod.reproduce_simple(self.genomes[i], self.genomes[j])
                        if child_genome is not None:
                            # spawn child at midpoint
                            cx = (self.positions[i, 0] + self.positions[j, 0]) / 2.0
                            cy = (self.positions[i, 1] + self.positions[j, 1]) / 2.0
                            self._spawn_child(cx, cy, child_genome, child_species)
                    except Exception:
                        continue

    def _spawn_child(self, x: float, y: float, genome_obj, species_name: str):
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
        self.count += 1
        return idx

    def _attempt_asexual_division(self, world):
        """Asexual 1->2 division based on internal resources and a replication gene.
        This is intentionally strict so early mortality is high.
        """
        if self.internal_resources is None or self._metabolism_mod is None:
            return

        # indexes into the internal resource vector
        idx_e = self._metabolism_mod.IDX_ENERGY
        idx_o = self._metabolism_mod.IDX_ORGANICS
        idx_m = self._metabolism_mod.IDX_MEMBRANE
        idx_info = self._metabolism_mod.IDX_INFO

        for i in range(self.count):
            if not self.alive[i]:
                continue
            genome_obj = self.genomes[i]
            if genome_obj is None:
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

            # All minimal conditions met: metabolic_stress controlla se e come dividere.
            # Replica attiva solo se lo stress non è estremo; il tasso di mutazione
            # aumenta con lo stress metabolico.
            e = float(stocks[idx_e])
            avg = float(self._energy_avg[i])
            var = float(self._energy_var[i])
            energy_deficit_signal = max(0.0, 0.5 - e)
            homeostasis_error = var
            metabolic_stress = energy_deficit_signal + homeostasis_error

            # se lo stress è molto basso, la divisione è ancora più rara
            if metabolic_stress < 0.02:
                continue

            from pixel.genome import Genome
            import numpy as _np
            try:
                base = _np.asarray(genome_obj.data, dtype=float)
                # sigma di mutazione cresce con lo stress, mantenendo un minimo/massimo
                sigma = 0.003 + min(0.03, metabolic_stress * 0.1)
                mutated = base + _np.random.normal(scale=sigma, size=base.shape)
                child_genome = Genome(data=mutated)
            except Exception:
                child_genome = genome_obj

            # spawn child near parent
            cx = float(self.positions[i, 0]) + (np.random.rand() - 0.5) * 0.5
            cy = float(self.positions[i, 1]) + (np.random.rand() - 0.5) * 0.5
            child_idx = self._spawn_child(cx, cy, child_genome, self.species[i])
            if child_idx is None:
                continue

            # share internal resources roughly equally, with a cost
            child_stocks = self.internal_resources[child_idx]
            child_stocks[:] = stocks * 0.4  # child receives 40%
            stocks[:] *= 0.4                 # parent keeps 40%
            # 20% lost as division overhead, implicitly

            # extra energetic cost of division
            stocks[idx_e] *= 0.8
            child_stocks[idx_e] *= 0.8

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
        import numpy as _np
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _np.savez_compressed(path, positions=self.positions[:self.count], energies=self.energies[:self.count], species=self.species[:self.count])

    def load(self, path: str):
        import numpy as _np
        data = _np.load(path, allow_pickle=True)
        pos = data["positions"]
        n = pos.shape[0]
        self.count = min(n, self.capacity)
        self.positions[:self.count] = pos[:self.count]
        self.energies[:self.count] = data["energies"][:self.count]
        sp = data["species"][:self.count]
        for i in range(self.count):
            self.species[i] = str(sp[i])

# End of pixel module skeleton

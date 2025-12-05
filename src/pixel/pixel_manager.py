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
        # species names
        self.species: List[str] = ["unknown"] * capacity
        # optional genomes storage (only if genome module available)
        self.genomes = [None] * capacity

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
        if self.has_reproduction:
            self._reproduction_mod = importlib.import_module("pixel.reproduction")

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
            self.species[idx] = f"{species_prefix}_{np.random.randint(0,9999)}"
            # if genome module available, assign random genome
            if self.has_genome and self._genome_mod is not None:
                try:
                    self.genomes[idx] = self._genome_mod.random_genome()
                except Exception:
                    self.genomes[idx] = None
            ids.append(idx)
            self.count += 1
        return ids

    def step(self, dt: float, world, resource_grid=None):
        """Advance simulation by dt seconds (or ticks)."""
        # simple loop for clarity (vectorization later)
        for i in range(self.count):
            if not self.alive[i]:
                continue
            x, y = float(self.positions[i, 0]), float(self.positions[i, 1])
            e = float(self.energies[i])

            # decide action
            if e < 0.4:
                # try to eat at current tile or nearby
                eaten = False
                if resource_grid is not None:
                    tx, ty = int(round(x)), int(round(y))
                    # try atoms in order of beneficial effect
                    for atom_idx, atom in enumerate(resource_grid.__class__.__dict__.get('ATOM_TYPES', [])):
                        # fall back to direct list if class attribute not present
                        pass
                    # use the public ATOM_TYPES list if present
                    atom_list = getattr(resource_grid, 'atom_types', None)
                    # our resources module exposes ATOM_TYPES at module level; try fallback
                    try:
                        from world.resources import ATOM_TYPES as GLOBAL_ATOMS
                        atom_list = GLOBAL_ATOMS
                    except Exception:
                        atom_list = getattr(resource_grid, 'ATOM_TYPES', None)

                    if atom_list is None:
                        # fallback: simply consume first index if any
                        if resource_grid is not None:
                            if resource_grid.consume_atom(tx, ty, 0, amount=1):
                                # simple energy gain
                                gain = 0.05
                                self.energies[i] = min(1.0, e + gain)
                                eaten = True
                    else:
                        # try to consume the best atom by effect (use metabolism module if present)
                        best_gain = -999.0
                        best_j = None
                        for j, atom_symbol in enumerate(atom_list):
                            # compute effect
                            gain = 0.0
                            if self.has_metabolism and self._metabolism_mod is not None:
                                try:
                                    gain = self._metabolism_mod.nutrient_to_energy(atom_symbol)
                                except Exception:
                                    gain = 0.0
                            else:
                                # fallback: small positive for P, negative for X, else zero
                                if atom_symbol == 'P':
                                    gain = 0.05
                                elif atom_symbol == 'X':
                                    gain = -0.2
                                elif atom_symbol == 'Cl':
                                    gain = -0.02
                            if gain > best_gain:
                                best_gain = gain
                                best_j = j
                        if best_j is not None:
                            if resource_grid.consume_atom(tx, ty, best_j, amount=1):
                                self.energies[i] = float(min(1.0, e + max(0.0, best_gain)))
                                eaten = True
                if not eaten:
                    # if can't eat, wander
                    nx, ny = self._random_walk(x, y)
                    self.positions[i, 0] = nx
                    self.positions[i, 1] = ny
            else:
                # normal behavior: move towards resource-rich tiles
                try:
                    from pixel.behaviors import decide_move

                    nx, ny = decide_move(x, y, world, resource_grid, perception=3)
                except Exception:
                    nx, ny = self._random_walk(x, y)
                self.positions[i, 0] = nx
                self.positions[i, 1] = ny

            # apply metabolic cost
            if self.has_metabolism and self._metabolism_mod is not None:
                try:
                    self._metabolism_mod.apply_metabolic_costs(self.energies, dt)
                except Exception:
                    # fallback
                    self.energies[i] = float(self.energies[i] - 0.001 * dt)
            else:
                self.energies[i] = float(self.energies[i] - 0.001 * dt)

            # clamp and death
            self._clamp(i, world)
            if self.energies[i] <= 0.0:
                self.alive[i] = False

        # after movement, attempt reproduction in a very naive way
        if self.has_reproduction and self._reproduction_mod is not None:
            self._attempt_reproduction(world)
        else:
            # optional: print hint that reproduction module not present
            pass

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
        self.count += 1
        return idx

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

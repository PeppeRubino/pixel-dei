
# --------------------------------------------------------
# File: src/world/resources.py
"""
Simple resource (atoms) system.
Each tile has a dict-like distribution of atoms. For simplicity we represent
atoms as integer counts in a structured NumPy array with a fixed list of atom types.

Atoms affect Pixel health (+/-) or may unlock traits. The mutation-related
effects are currently commented out as requested.
"""
from typing import Dict, List, Tuple
import numpy as np
import os

ATOM_TYPES: List[str] = [
    "H", "C", "N", "O", "P", "S",  # common biologically relevant atoms
    "Fe", "Si", "Na", "Cl",        # minerals, salts
    "X"  # placeholder for toxic/rare atoms
]


class ResourceGrid:
    def __init__(self, shape: Tuple[int, int], initial_counts: int = 10):
        self.h, self.w = shape
        self._grid = np.full((self.h, self.w, len(ATOM_TYPES)), int(initial_counts), dtype=np.int32)

    def sample_atom_at(self, x: int, y: int, atom_index: int) -> int:
        return int(self._grid[y, x, atom_index])

    def consume_atom(self, x: int, y: int, atom_index: int, amount: int = 1) -> bool:
        """Consume atoms if available. Return True if consumed."""
        if self._grid[y, x, atom_index] >= amount:
            self._grid[y, x, atom_index] -= amount
            return True
        return False

    def replenish(self, rate: float = 0.01):
        """Simple replenishment step (add small counts back)."""
        add = (np.random.rand(self.h, self.w, len(ATOM_TYPES)) < rate).astype(np.int32)
        self._grid += add

    def atom_counts(self) -> np.ndarray:
        return self._grid

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path, grid=self._grid)

    def load(self, path: str):
        data = np.load(path)
        self._grid = data["grid"]


# Effect mapping: how each atom influences health or traits
# Positive values heal, negative values damage. Trait-unlocking is commented.
ATOM_EFFECTS: Dict[str, int] = {
    "H": 0,
    "C": 0,
    "N": 0,
    "O": 0,
    "P": 1,   # small positive effect example
    "S": 0,
    "Fe": 0,
    "Si": 0,
    "Na": 0,
    "Cl": -1,  # example: high chlorine could be harmful
    "X": -5,    # toxic
}


def atom_effect(atom_symbol: str) -> int:
    return ATOM_EFFECTS.get(atom_symbol, 0)


# Mutation unlocking example (commented)
# def try_unlock_mutation(pixel_genome, atom_symbol):
#     """
#     If a pixel consumes a specific rare atom, it could unlock a mutation flag
#     in its genome. This functionality is intentionally left commented out.
#     """
#     if atom_symbol == 'X':
#         pixel_genome['mutations'].append('toxic_resistance')

# End of resources.py
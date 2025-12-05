

# -------------------------------------------------
# src/pixel/metabolism.py
"""
Minimal metabolism interface. In future this will implement
complex chemical interactions. For now expose a simple API:
  - apply_metabolic_costs(pixel_ids, energies, dt)
  - nutrient_to_energy(atom_symbol) -> float

If this module is absent, PixelManager will fallback to simple
energy -= dt * base_cost behaviour.
"""
from typing import List

# map atom symbol -> energy effect (per atom consumed)
NUTRIENT_ENERGY = {
    "P": 0.05,
    "Cl": -0.02,
    "X": -0.2,
}


def apply_metabolic_costs(energies, dt: float, base_cost: float = 0.001):
    """Modify the provided energy array in-place.
    This is intentionally simple: subtract base_cost * dt from each.
    """
    energies -= base_cost * dt


def nutrient_to_energy(atom_symbol: str) -> float:
    return float(NUTRIENT_ENERGY.get(atom_symbol, 0.0))

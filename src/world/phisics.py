
# --------------------------------------------------------
# File: src/world/physics.py
"""
Minimal physics helpers. There is intentionally no collision system.
Only helper functions for movement and boundary handling.
"""
from typing import Tuple
import numpy as np


def clamp_position(pos: Tuple[float, float], bounds: Tuple[int, int]) -> Tuple[float, float]:
    x, y = pos
    w, h = bounds
    x = max(0.0, min(float(w - 1), x))
    y = max(0.0, min(float(h - 1), y))
    return x, y


def move_random_walk(x: float, y: float, speed: float = 1.0) -> Tuple[float, float]:
    # lightweight random walk step (returns new float coords)
    dx = (np.random.rand() - 0.5) * 2.0 * speed
    dy = (np.random.rand() - 0.5) * 2.0 * speed
    return x + dx, y + dy


# Rule (commented): prevent crossing from water to land unless condition met
# def can_cross_water_to_land(from_biome, to_biome, pixel_traits):
#     """
#     Example rule placeholder: if moving from WATER/OCEAN to BEACH/GRASSLAND
#     require pixel_traits.has('amphibious') or energy > threshold.
#     Currently commented as requested.
#     """
#     if from_biome in (Biome.OCEAN, Biome.LAKE) and to_biome not in (Biome.OCEAN, Biome.LAKE, Biome.RIVER):
#         return pixel_traits.get('amphibious', False) and pixel_traits.get('energy',0) > 10
#     return True

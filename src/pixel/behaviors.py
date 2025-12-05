# -------------------------------------------------
# src/pixel/behaviors.py
"""
Simple behavior heuristics for Pixels. These are intentionally small
and deterministic enough to be testable.
"""
from typing import Tuple, Optional
import numpy as np


def decide_move(x: float, y: float, world, resource_grid, perception: int = 3) -> Tuple[float, float]:
    """
    Look in a local square neighborhood (perception) and move towards the
    tile with the highest total nutrient counts. If none better, random walk.

    world: World instance (must have size attributes)
    resource_grid: ResourceGrid or None
    """
    h, w = world.size[1], world.size[0]
    best_score = -1.0
    best_pos = (x, y)
    cx, cy = int(round(x)), int(round(y))
    rng = range(-perception, perception + 1)
    for dy in rng:
        for dx in rng:
            nx = cx + dx
            ny = cy + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            score = 0.0
            if resource_grid is not None:
                # sum of all atoms in that tile
                tile_counts = resource_grid.atom_counts()[ny, nx]
                score = float(tile_counts.sum())
            if score > best_score:
                best_score = score
                best_pos = (float(nx) + 0.5, float(ny) + 0.5)
    # small step towards best_pos
    step = 1.0
    tx, ty = best_pos
    dx = tx - x
    dy = ty - y
    dist = np.hypot(dx, dy)
    if dist < 1e-6:
        # random jitter
        return x + (np.random.rand() - 0.5), y + (np.random.rand() - 0.5)
    nx = x + (dx / dist) * min(step, dist)
    ny = y + (dy / dist) * min(step, dist)
    return nx, ny

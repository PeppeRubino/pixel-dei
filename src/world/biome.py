# File: src/world/biome.py
"""
Biome definitions and utilities.
"""
from enum import Enum
from typing import Tuple

# Simple RGB color tuples for rendering
BIOME_COLORS = {
    "OCEAN": (20, 40, 180),
    "WATER": (40, 120, 200),
    "BEACH": (238, 214, 175),
    "DESERT": (233, 196, 106),
    "GRASSLAND": (106, 190, 48),
    "FOREST": (30, 120, 40),
    "MOUNTAIN": (120, 120, 120),
    "SNOW": (240, 240, 240),
    "VOLCANIC": (150, 40, 30),
    "LAKE": (30, 90, 170),
    "RIVER": (50, 120, 200),
}


class Biome(Enum):
    OCEAN = "OCEAN"
    WATER = "WATER"
    BEACH = "BEACH"
    DESERT = "DESERT"
    GRASSLAND = "GRASSLAND"
    FOREST = "FOREST"
    MOUNTAIN = "MOUNTAIN"
    SNOW = "SNOW"
    VOLCANIC = "VOLCANIC"
    LAKE = "LAKE"
    RIVER = "RIVER"


def color_for_biome(b: Biome) -> Tuple[int, int, int]:
    return BIOME_COLORS.get(b.value, (255, 0, 255))


def biome_from_env(elevation: float, temperature: float, humidity: float, pressure: float) -> Biome:
    """
    Map environmental scalar values (ranges typically 0..1) to a Biome enum.
    This is intentionally simple and deterministic; later you can
    replace with probabilistic or ML-based classifiers.
    """
    # water threshold
    if elevation < 0.15:
        return Biome.OCEAN
    if elevation < 0.18 and humidity > 0.6:
        return Biome.LAKE

    # beach narrow band
    if elevation < 0.2 and elevation >= 0.15:
        return Biome.BEACH

    # volcanoes: hot + high elevation + low humidity
    if elevation > 0.75 and temperature > 0.6 and humidity < 0.3:
        return Biome.VOLCANIC

    # mountains and snow
    if elevation > 0.75:
        if temperature < 0.35:
            return Biome.SNOW
        return Biome.MOUNTAIN

    # deserts: hot and dry
    if temperature > 0.75 and humidity < 0.2:
        return Biome.DESERT

    # forests: moderate temp and high humidity
    if humidity > 0.6 and temperature > 0.25:
        return Biome.FOREST

    # grasslands
    if humidity > 0.2 and temperature > 0.2:
        return Biome.GRASSLAND

    # fallback
    return Biome.GRASSLAND










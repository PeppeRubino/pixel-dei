# File: src/world/biome.py
"""
Biome definitions and utilities.
The classifier is inspired by an earlier probabilistic zone generator,
but uses deterministic rules over normalized fields with a pinch of
local noise to avoid banded artefacts.
"""

from enum import Enum
from typing import Tuple


# Simple RGB color tuples for rendering.
# Colors are intentionally vivid so biomes are easy to distinguish.
BIOME_COLORS = {
    "OCEAN": (10, 40, 140),
    "WATER": (40, 140, 210),
    # Slightly warmer, less white than before
    "BEACH": (235, 210, 170),
    # Deserts a bit more saturated so they do not look like snow
    "DESERT": (225, 185, 90),
    "ROCK_DESERT": (195, 165, 85),
    # Pre‑biotic "grasslands"/plains are resembled with more arid tones;
    # il vero verde apparirà solo tramite shading futuro.
    "GRASSLAND": (170, 190, 120),
    "FOREST": (34, 139, 34),
    "RAINFOREST": (5, 120, 60),
    "SAVANNA": (200, 170, 80),
    "SWAMP": (40, 80, 50),
    "MANGROVE": (30, 120, 90),
    "MOUNTAIN": (150, 150, 160),
    "HILLS": (160, 180, 120),
    "PLAIN": (190, 200, 130),
    "TUNDRA": (170, 190, 210),
    "SNOW": (245, 245, 245),
    "GLACIER": (210, 235, 255),
    "VOLCANIC": (170, 45, 35),
    "LAKE": (40, 110, 210),
    "RIVER": (70, 160, 230),
}


class Biome(Enum):
    OCEAN = "OCEAN"
    WATER = "WATER"
    BEACH = "BEACH"
    DESERT = "DESERT"
    ROCK_DESERT = "ROCK_DESERT"
    GRASSLAND = "GRASSLAND"
    FOREST = "FOREST"
    RAINFOREST = "RAINFOREST"
    SAVANNA = "SAVANNA"
    SWAMP = "SWAMP"
    MANGROVE = "MANGROVE"
    MOUNTAIN = "MOUNTAIN"
    HILLS = "HILLS"
    PLAIN = "PLAIN"
    TUNDRA = "TUNDRA"
    SNOW = "SNOW"
    GLACIER = "GLACIER"
    VOLCANIC = "VOLCANIC"
    LAKE = "LAKE"
    RIVER = "RIVER"


def color_for_biome(b: Biome) -> Tuple[int, int, int]:
    """Return RGB color for a biome, using a vivid fallback if missing."""
    return BIOME_COLORS.get(b.value, (255, 0, 255))


def biome_from_env(
    elevation: float,
    temperature: float,
    humidity: float,
    pressure: float,
    global_o2: float = 0.21,
    organic_layer: float = 0.0,
    mineral_layer: float = 0.0,
    vegetation_index: float = 0.0,
    local_noise: float = 0.0,
) -> Biome:
    """
    Map environmental scalar values (0..1) to a Biome enum.

    Parameters
    ----------
    elevation : float
        Normalized elevation (0 = deep ocean, 1 = highest peaks).
    temperature : float
        Normalized temperature (0 = coldest, 1 = hottest).
    humidity : float
        Normalized humidity (0 = driest, 1 = most humid).
    pressure : float
        Used as a proxy for latitude: 0 ~ poles, 1 ~ equator.
    global_o2 : float, optional
        Approximate global atmospheric O2 fraction. Higher values allow
        more energetically expensive biomes (forests, complex ecosystems).
    organic_layer : float, optional
        Slow memory of accumulated organic matter (from deaths, detritus).
    mineral_layer : float, optional
        Local mineral/ion enrichment (currently unused here but kept
        for future extensions).
    vegetation_index : float, optional
        Placeholder for density of structured phototrophs.
    local_noise : float, optional
        Small-scale spatial noise in [0,1] used to break perfect bands
        and give continents a more fragmented look.
    """
    alt = elevation
    temp = temperature
    hum = humidity
    lat_frac = pressure  # 0 at poles, 1 at equator
    n = max(0.0, min(1.0, local_noise))

    # ------------------------
    # WATER & COASTLINE
    # ------------------------

    if alt < 0.12:
        return Biome.OCEAN

    # Shallow water / lakes near land
    if alt < 0.16:
        if hum > 0.55:
            return Biome.LAKE
        return Biome.WATER

    # Narrow coastal band
    if 0.16 <= alt < 0.20:
        return Biome.BEACH

    # ------------------------
    # EXTREME ALTITUDE (MOUNTAINS, GLACIERS, VOLCANOES)
    # ------------------------

    # Glaciers only at sufficiently polar latitudes, never at the equator
    if alt > 0.85 and temp < 0.35 and lat_frac < 0.35:
        return Biome.GLACIER

    if alt > 0.80 and hum < 0.25 and temp > 0.6:
        # High, dry, hot -> volcanic
        return Biome.VOLCANIC

    if alt > 0.80:
        # Permanent snow only outside the tropical belt
        if temp < 0.35 and lat_frac < 0.4:
            return Biome.SNOW
        return Biome.MOUNTAIN

    # ------------------------
    # POLAR & SUB-POLAR REGIONS
    # ------------------------

    polar_region = lat_frac < 0.25
    if polar_region and alt > 0.50:
        if temp < 0.35:
            return Biome.TUNDRA
        return Biome.SNOW

    # ------------------------
    # DESERTS & ARID ZONES
    # ------------------------

    # Equatorial-to-subtropical dry belt: we want a warm/dry centre
    # concentrated near the equator (lat_frac high).
    if temp > 0.6 and hum < 0.45 and lat_frac > 0.45:
        if alt > 0.55:
            return Biome.ROCK_DESERT
        return Biome.DESERT

    # Very hot & dry anywhere -> desert
    if temp > 0.8 and hum < 0.35:
        return Biome.DESERT

    # ------------------------
    # PRE-BIOTIC LAND SURFACES: NO MACRO VEGETATION
    # ------------------------

    # When the organic layer is essentially absent the surface cannot yet
    # support true grasslands/forests. We use "barren" variants but mix
    # them with local_noise so continents are patchy, not banded.
    if organic_layer < 0.02:
        warm = temp > 0.55
        mid = 0.30 < temp <= 0.55

        if warm:
            # Warm belt: mix of deserts, rocky deserts and some bare plains
            if hum < 0.35:
                return Biome.ROCK_DESERT if n > 0.4 else Biome.DESERT
            if hum < 0.6:
                if alt > 0.6 and n > 0.6:
                    return Biome.MOUNTAIN
                return Biome.ROCK_DESERT if n > 0.5 else Biome.DESERT
            # Warmer but more humid -> barren plains/hills
            return Biome.PLAIN if n > 0.3 else Biome.HILLS

        if mid:
            # Temperate but pre-biotic: hills, plains and some mountains
            if alt < 0.35:
                return Biome.PLAIN if n > 0.2 else Biome.DESERT
            if alt < 0.65:
                return Biome.HILLS if n > 0.3 else Biome.ROCK_DESERT
            return Biome.MOUNTAIN

        # Cold but not yet polar/tundra from the earlier branch
        if alt > 0.65 and n > 0.4:
            return Biome.MOUNTAIN
        return Biome.ROCK_DESERT if n > 0.5 else Biome.TUNDRA

    # ------------------------
    # TROPICAL FORESTS / RAINFORESTS
    # ------------------------

    very_humid = hum > 0.8
    rich_soil = organic_layer > 0.2
    oxygen_ok = global_o2 > 0.15
    if lat_frac > 0.4 and very_humid and temp > 0.6 and rich_soil and oxygen_ok:
        return Biome.RAINFOREST

    # ------------------------
    # WETLANDS / MANGROVES / SWAMPS
    # ------------------------

    if hum > 0.7 and alt < 0.35:
        if lat_frac > 0.4:
            return Biome.MANGROVE
        return Biome.SWAMP

    # ------------------------
    # TEMPERATE MIXED ZONES
    # ------------------------

    # Transitional: moderate humidity and temperature
    if 0.3 < hum < 0.6 and 0.3 < temp < 0.7:
        if alt < 0.35:
            return Biome.PLAIN
        if alt < 0.6:
            return Biome.HILLS
        return Biome.MOUNTAIN

    # Forests: fairly humid and not too cold, with sufficient oxygen and soil
    if hum > 0.6 and temp > 0.3 and oxygen_ok and organic_layer > 0.1:
        return Biome.FOREST

    # Savanna: warm and seasonally dry
    if hum > 0.35 and temp > 0.5:
        return Biome.SAVANNA

    # Grasslands as mild default for non-extreme conditions
    if hum > 0.2 and temp > 0.2:
        return Biome.GRASSLAND

    # ------------------------
    # FALLBACK
    # ------------------------

    return Biome.GRASSLAND

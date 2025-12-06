# File: src/world/biome.py
"""
Biome definitions and utilities.
The classifier is inspired by an earlier probabilistic zone generator,
but uses deterministic rules over normalized fields.
"""
from enum import Enum
from typing import Tuple


# Simple RGB color tuples for rendering
# Colors are intentionally vivid to make the map visually rich.
BIOME_COLORS = {
    "OCEAN": (10, 40, 140),
    "WATER": (40, 140, 210),
    "BEACH": (242, 220, 180),
    "DESERT": (240, 200, 120),
    "ROCK_DESERT": (210, 180, 110),
    "GRASSLAND": (110, 200, 65),
    "FOREST": (34, 139, 34),
    "RAINFOREST": (5, 120, 60),
    "SAVANNA": (200, 170, 80),
    "SWAMP": (40, 80, 50),
    "MANGROVE": (30, 120, 90),
    "MOUNTAIN": (150, 150, 160),
    "HILLS": (140, 170, 100),
    "PLAIN": (160, 200, 110),
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
    # Use a vivid magenta as explicit fallback if a biome has no color
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
        Approximate global atmospheric O₂ fraction. Higher values allow
        more energetically expensive biomi (foreste dense, ecosistemi complessi).
    organic_layer : float, optional
        Lenta memoria del suolo organico accumulato (da morti, detriti).
    mineral_layer : float, optional
        Arricchimento minerale/ioni nel suolo locale.
    vegetation_index : float, optional
        Placeholder per densità di fototrofi strutturati.
    """
    alt = elevation
    temp = temperature
    hum = humidity
    lat_frac = pressure  # 0 at poles, 1 at equator

    # ------------------------
    # WATER & COASTLINE
    # ------------------------

    if alt < 0.12:
        return Biome.OCEAN

    # Shallow water / lakes near land
    if alt < 0.16:
        if hum > 0.5:
            return Biome.LAKE
        return Biome.WATER

    # Narrow coastal band
    if 0.16 <= alt < 0.20:
        return Biome.BEACH

    # ------------------------
    # EXTREME ALTITUDE (MOUNTAINS, GLACIERS, VOLCANOES)
    # ------------------------

    if alt > 0.85 and temp < 0.35 and lat_frac < 0.25:
        # High + cold + near poles -> glaciers
        return Biome.GLACIER

    if alt > 0.80 and hum < 0.25 and temp > 0.6:
        # High, dry, hot -> volcanic
        return Biome.VOLCANIC

    if alt > 0.80:
        if temp < 0.35:
            return Biome.SNOW
        return Biome.MOUNTAIN

    # ------------------------
    # POLAR & SUB-POLAR REGIONS
    # ------------------------

    polar_region = lat_frac < 0.15 or lat_frac > 0.85
    if polar_region and alt > 0.50:
        # Tundra / glacier mix at high latitude + elevation
        if temp < 0.35:
            return Biome.TUNDRA
        return Biome.SNOW

    # ------------------------
    # DESERTS & ARID ZONES
    # ------------------------

    # Subtropical dry belt, broadly 0.2-0.6 of lat_frac
    if 0.2 < lat_frac < 0.6 and temp > 0.6 and hum < 0.35:
        # Rockier deserts at higher altitude
        if alt > 0.55:
            return Biome.ROCK_DESERT
        return Biome.DESERT

    # Very hot & dry anywhere -> desert
    if temp > 0.8 and hum < 0.25:
        return Biome.DESERT

    # ------------------------
    # TROPICAL FORESTS / RAINFORESTS (dipendono da O₂ e suolo organico)
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
        # Warmer latitudes -> mangroves, cooler -> swamp
        if lat_frac > 0.4:
            return Biome.MANGROVE
        return Biome.SWAMP

    # ------------------------
    # TEMPERATE MIXED ZONES (GRASSLAND / FOREST / SAVANNA / HILLS)
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









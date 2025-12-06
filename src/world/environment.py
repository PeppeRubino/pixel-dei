# --------------------------------------------------------
# File: src/world/environment.py
#
# Environmental resource channels per biome.
# These are the "raw" inputs that cells can convert into
# internal resources (ENERGY, ORGANICS, MINERALS, MEMBRANE, ...).
# --------------------------------------------------------

from typing import Dict, Tuple
import math
import random

import numpy as np

from .biome import Biome

# Environmental channels (raw inputs)
ENV_CHANNELS = [
    "LIGHT",          # photosynthetic light availability
    "ORGANIC_SOUP",   # dissolved / particulate organics
    "H2S",            # reduced sulfur compounds
    "FE2",            # ferrous iron / metals
    "CO2",            # inorganic carbon
    "HEAT_GRADIENT",  # thermal gradients / vents
]

EnvProfile = Dict[str, Tuple[float, float, float]]
# channel -> (mean, variability, seasonality_amplitude)


def _base_profile_for_biome(biome: Biome, lat_frac: float) -> EnvProfile:
    """Return base (mean, variability, season) per channel for a biome.
    Values are in [0, 1]-ish; noise and seasonality will be applied at sample time.
    """
    # Defaults: low everything
    prof: EnvProfile = {
        "LIGHT": (0.2, 0.05, 0.1),
        "ORGANIC_SOUP": (0.1, 0.05, 0.05),
        "H2S": (0.0, 0.02, 0.0),
        "FE2": (0.05, 0.05, 0.02),
        "CO2": (0.4, 0.05, 0.05),
        "HEAT_GRADIENT": (0.0, 0.02, 0.0),
    }

    hot = lat_frac > 0.6
    cold = lat_frac < 0.25

    if biome in (Biome.RAINFOREST, Biome.FOREST):
        prof["LIGHT"] = (0.7, 0.1, 0.15)
        prof["ORGANIC_SOUP"] = (0.8, 0.1, 0.2)
        prof["CO2"] = (0.6, 0.05, 0.05)
    elif biome == Biome.SAVANNA or biome == Biome.GRASSLAND or biome == Biome.PLAIN:
        prof["LIGHT"] = (0.8, 0.1, 0.2)
        prof["ORGANIC_SOUP"] = (0.4, 0.1, 0.3)
    elif biome in (Biome.DESERT, Biome.ROCK_DESERT):
        prof["LIGHT"] = (0.95, 0.05, 0.2)
        prof["ORGANIC_SOUP"] = (0.05, 0.03, 0.1)
        prof["CO2"] = (0.7, 0.05, 0.05)
    elif biome in (Biome.MANGROVE, Biome.SWAMP):
        prof["LIGHT"] = (0.6, 0.1, 0.15)
        prof["ORGANIC_SOUP"] = (0.9, 0.1, 0.2)
    elif biome == Biome.LAKE or biome == Biome.RIVER:
        prof["LIGHT"] = (0.7, 0.1, 0.15)
        prof["ORGANIC_SOUP"] = (0.7, 0.1, 0.25)
    elif biome == Biome.OCEAN or biome == Biome.WATER:
        prof["LIGHT"] = (0.8, 0.1, 0.1)
        prof["ORGANIC_SOUP"] = (0.4, 0.1, 0.1)
    if biome == Biome.VOLCANIC:
        prof["HEAT_GRADIENT"] = (0.9, 0.05, 0.05)
        prof["H2S"] = (0.5, 0.1, 0.05)
        prof["FE2"] = (0.4, 0.1, 0.05)
    if biome in (Biome.SNOW, Biome.GLACIER, Biome.TUNDRA) or cold:
        # cold regions: low liquid organics, low light at extreme
        prof["LIGHT"] = (min(prof["LIGHT"][0], 0.4), 0.05, 0.05)
        prof["ORGANIC_SOUP"] = (prof["ORGANIC_SOUP"][0] * 0.6, 0.05, 0.05)
    return prof


def sample_environment(biome: Biome, lat_frac: float, t: float) -> Dict[str, float]:
    """Sample environmental channels for a biome at time t.
    Adds simple Gaussian noise and sinusoidal seasonality.
    """
    prof = _base_profile_for_biome(biome, lat_frac)
    season_phase = 2.0 * math.pi * (t / 1000.0)  # arbitrary period
    env: Dict[str, float] = {}
    for ch in ENV_CHANNELS:
        mean, var, season_amp = prof[ch]
        seasonal = season_amp * math.sin(season_phase)
        noise = random.gauss(0.0, var)
        val = mean + seasonal + noise
        env[ch] = max(0.0, float(val))
    return env


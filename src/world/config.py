# --------------------------------------------------------
# File: src/world/config.py
#
# Global-scale constants for world generation.
# These are kept separate so tweaking climate is easy.
# --------------------------------------------------------

# Physical-ish temperatures in degrees Celsius
# Equator a bit hotter, poles a bit colder to accentuate contrast.
EQUATOR_TEMP_C = 34.0   # warm equatorial mean
POLE_TEMP_C = -20.0     # cold polar mean

# How much temperature drops between sea level and maximum elevation
LAPSE_RATE_C_PER_ELEV = 25.0

# Random temperature noise amplitude (± degrees C around the latitudinal mean)
TEMP_NOISE_AMPL_C = 6.0

# Humidity tuning
HUMIDITY_OCEAN = 1.0
HUMIDITY_LAND_SCALE = 0.85

# Percentile used to decide how much of the planet is land vs ocean
# Slightly higher value -> less land, more fragmented continents/islands
CONTINENT_THRESHOLD_PERCENTILE = 60.0

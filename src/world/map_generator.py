# --------------------------------------------------------
# File: src/world/map_generator.py
"""
Global Earth-like FAST map generator.
Produces fragmented continents, large oceans, polar ice, deserts and forests.
Optimized for high resolutions (1024x512 and above).
"""
import os
import time
import random
from typing import Optional, Tuple

import numpy as np
from noise import pnoise2
from PIL import Image

from .biome import biome_from_env
from .config import (
    EQUATOR_TEMP_C,
    POLE_TEMP_C,
    LAPSE_RATE_C_PER_ELEV,
    TEMP_NOISE_AMPL_C,
    HUMIDITY_OCEAN,
    HUMIDITY_LAND_SCALE,
    CONTINENT_THRESHOLD_PERCENTILE,
)


class MapGenerator:
    def __init__(self, size: Tuple[int, int] = (1024, 512), seed: Optional[int] = None):
        self.width, self.height = size
        self.seed = seed if seed is not None else int(time.time())
        self._rng = random.Random(self.seed)
        # Offsets de-correlate different worlds while keeping determinism per seed
        self._offset_x = self._rng.randint(0, 10_000)
        self._offset_y = self._rng.randint(0, 10_000)

    # --------------------------------------------------------
    # MAIN GENERATION (VECTORIZED & FAST)
    # --------------------------------------------------------

    def generate(self, save_path: Optional[str] = None) -> dict:

        if save_path and os.path.exists(save_path):
            try:
                data = np.load(save_path)
                if data["elevation"].shape == (self.height, self.width):
                    return dict(data)
            except Exception:
                pass

        # -------------------------------
        # 1) CONTINENT MASK (FRAGMENTED)
        # -------------------------------

        base = self._make_noise(scale=1000.0, octaves=2)
        detail = self._make_noise(scale=260.0, octaves=4)
        rift = self._make_noise(scale=90.0, octaves=5)
        shred = self._make_noise(scale=45.0, octaves=5)

        base = self._normalize(base)
        detail = self._normalize(detail)
        rift = self._normalize(rift)

        continent_mask = 0.45 * base + 0.30 * detail - 0.30 * rift + 0.15 * shred
        continent_mask = self._normalize(continent_mask)

        # Use a percentile-based threshold so land/ocean balance adapts across seeds
        land_threshold = float(np.percentile(continent_mask, CONTINENT_THRESHOLD_PERCENTILE))
        land = continent_mask > land_threshold

        # -------------------------------
        # 2) ELEVATION
        # -------------------------------

        terrain = self._normalize(self._make_noise(scale=140.0, octaves=5))
        elevation = np.where(land, 0.25 + 0.75 * terrain, 0.05 * terrain)
        elevation = self._normalize(elevation)

        # -------------------------------
        # 3) LATITUDE FIELD (0 POLES, 1 EQUATOR)
        # -------------------------------

        rows = np.arange(self.height, dtype=np.float32)
        lat_frac_1d = 1.0 - np.abs(rows - self.height / 2.0) / (self.height / 2.0)
        lat_frac_1d = np.clip(lat_frac_1d, 0.0, 1.0)
        lat_frac = np.tile(lat_frac_1d[:, None], (1, self.width))

        # -------------------------------
        # 4) GLOBAL TEMPERATURE (PHYSICAL, THEN NORMALIZED)
        # -------------------------------

        # Base physical temperature in °C from latitude
        temp_base_c = POLE_TEMP_C + (EQUATOR_TEMP_C - POLE_TEMP_C) * lat_frac

        # Add some coherent noise as small ± variation
        temp_noise = self._normalize(self._make_noise(scale=180.0, octaves=3))
        temp_noise_c = (temp_noise - 0.5) * (2.0 * TEMP_NOISE_AMPL_C)

        # Cool with elevation
        # elevation is 0..1, interpret as fraction of max elevation span
        alt_cooling_c = elevation * LAPSE_RATE_C_PER_ELEV

        temp_c = temp_base_c + temp_noise_c - alt_cooling_c
        temp_c = np.clip(temp_c, POLE_TEMP_C, EQUATOR_TEMP_C)

        # Normalize back to 0..1 for the rest of the engine
        temperature = (temp_c - POLE_TEMP_C) / (EQUATOR_TEMP_C - POLE_TEMP_C + 1e-12)
        temperature = np.clip(temperature, 0.0, 1.0)

        # -------------------------------
        # 5) HUMIDITY (LATITUDE + OROGRAPHY)
        # -------------------------------

        humidity_noise = self._normalize(self._make_noise(scale=160.0, octaves=4))

        # More humid near equator, drier near poles
        humidity = humidity_noise * (0.6 + 0.4 * lat_frac)
        # Mountains tend to be drier, valleys more humid
        humidity *= (1.0 - 0.3 * elevation)

        # Oceans are very humid; land scaled down a bit
        humidity = np.where(land, humidity * HUMIDITY_LAND_SCALE, HUMIDITY_OCEAN)
        humidity = self._normalize(humidity)

        # -------------------------------
        # 6) LATITUDE / PRESSURE PROXY
        # -------------------------------

        # Encode normalized latitude (0=poles, 1=equator) into the "pressure" field.
        # biome_from_env uses this to approximate climatic zones.
        pressure = lat_frac

        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            np.savez_compressed(
                save_path,
                elevation=elevation,
                humidity=humidity,
                temperature=temperature,
                pressure=pressure
            )

        return {
            "elevation": elevation,
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
        }

    # --------------------------------------------------------
    # FAST NOISE (NO NESTED HEAVY OPS)
    # --------------------------------------------------------

    def _make_noise(self, scale=100.0, octaves=4) -> np.ndarray:
        arr = np.zeros((self.height, self.width), dtype=np.float32)
        freq = 1.0 / scale

        for y in range(self.height):
            ny = y * freq + self.seed
            for x in range(self.width):
                nx = x * freq + self.seed
                arr[y, x] = pnoise2(nx, ny, octaves=octaves, base=self.seed)

        return arr

    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        mn, mx = arr.min(), arr.max()
        return (arr - mn) / (mx - mn + 1e-12)

    def _temperature_from_latitude(self) -> np.ndarray:
        ny = np.linspace(0.0, 1.0, self.height)[:, None]
        lat_angle = (ny - 0.5) * np.pi
        insolation = np.cos(lat_angle)
        insolation = self._normalize(insolation)
        return np.tile(insolation, (1, self.width))

    # --------------------------------------------------------
    # DEBUG RENDER (FAST)
    # --------------------------------------------------------

    def render_preview(self, fields: dict, out_size=(1200, 530), save_path=None):

        h_src, w_src = fields["elevation"].shape
        out_w, out_h = out_size

        xs = (np.linspace(0, w_src - 1, out_w)).astype(np.int32)
        ys = (np.linspace(0, h_src - 1, out_h)).astype(np.int32)

        elev_r = fields["elevation"][np.ix_(ys, xs)]
        temp_r  = fields["temperature"][np.ix_(ys, xs)]
        hum_r   = fields["humidity"][np.ix_(ys, xs)]
        press_r = fields["pressure"][np.ix_(ys, xs)]

        rgb = np.zeros((out_h, out_w, 3), dtype=np.uint8)

        for j in range(out_h):
            for i in range(out_w):
                biome = biome_from_env(
                    float(elev_r[j, i]),
                    float(temp_r[j, i]),
                    float(hum_r[j, i]),
                    float(press_r[j, i])
                )
                rgb[j, i] = biome.color

        img = Image.fromarray(rgb, mode='RGB')
        if save_path:
            img.save(save_path)
        return img

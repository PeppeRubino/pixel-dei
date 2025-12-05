# --------------------------------------------------------
# File: src/world/map_generator.py
"""
Global Earth-like FAST map generator.
Produces fragmented continents, large oceans, polar ice, deserts and forests.
Optimized for high resolutions (1024x512 and above).
"""
import os
import time
import numpy as np
from noise import pnoise2
from typing import Optional, Tuple
from PIL import Image

from .biome import biome_from_env


class MapGenerator:
    def __init__(self, size: Tuple[int, int] = (1024, 512), seed: Optional[int] = None):
        self.width, self.height = size
        self.seed = seed if seed is not None else int(time.time())

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

        base = self._make_noise(scale=900.0, octaves=2)
        detail = self._make_noise(scale=220.0, octaves=4)
        rift = self._make_noise(scale=80.0, octaves=5)

        base = self._normalize(base)
        detail = self._normalize(detail)
        rift = self._normalize(rift)

        continent_mask = 0.6 * base + 0.25 * detail - 0.25 * rift
        continent_mask = self._normalize(continent_mask)

        land = continent_mask > 0.52

        # -------------------------------
        # 2) ELEVATION
        # -------------------------------

        terrain = self._normalize(self._make_noise(scale=140.0, octaves=5))
        elevation = np.where(land, 0.25 + 0.75 * terrain, 0.05 * terrain)
        elevation = self._normalize(elevation)

        # -------------------------------
        # 3) GLOBAL TEMPERATURE (LATITUDE)
        # -------------------------------

        lat_temp = self._temperature_from_latitude()
        temp_noise = self._normalize(self._make_noise(scale=180.0, octaves=3))

        temperature = 0.85 * lat_temp + 0.15 * temp_noise
        temperature -= 0.55 * elevation  # altitude cooling

        polar = np.abs(np.linspace(-1, 1, self.height))[:, None]
        polar = np.tile(polar, (1, self.width))
        temperature -= 0.35 * polar

        temperature = self._normalize(temperature)

        # -------------------------------
        # 4) HUMIDITY (FAST MODEL)
        # -------------------------------

        humidity = self._normalize(self._make_noise(scale=160.0, octaves=4))
        humidity = np.where(land, humidity * 0.85, 1.0)
        humidity = self._normalize(humidity)

        # -------------------------------
        # 5) PRESSURE
        # -------------------------------

        pressure = self._normalize(self._make_noise(scale=320.0, octaves=2))

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

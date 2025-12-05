# --------------------------------------------------------
# File: src/world/world.py
"""
World object: coordinates the map fields, biome classification and resource grid.
"""
from typing import Optional, Tuple
import numpy as np
import os

from .map_generator import MapGenerator
from .biome import biome_from_env, Biome, color_for_biome


class World:
    def __init__(self, size: Tuple[int, int] = (256, 256), seed: Optional[int] = None, map_path: Optional[str] = None):
        self.size = size
        self.seed = seed
        self.map_path = map_path
        self._loaded = False
        self.elevation = None
        self.temperature = None
        self.humidity = None
        self.pressure = None
        self.biome_map = None  # integer indices mapping to Biome
        self._generate_or_load()

    def _generate_or_load(self):
        gen = MapGenerator(size=self.size, seed=self.seed)
        data = gen.generate(save_path=self.map_path) if self.map_path else gen.generate()
        self.elevation = data["elevation"]
        self.temperature = data["temperature"]
        self.humidity = data["humidity"]
        self.pressure = data["pressure"]
        self._classify_biomes()
        self._loaded = True

    def _classify_biomes(self):
        h, w = self.elevation.shape
        self.biome_map = np.empty((h, w), dtype=np.uint8)
        # map Biome values to small ints
        mapping = {b: i for i, b in enumerate(Biome)}
        for y in range(h):
            for x in range(w):
                elev = float(self.elevation[y, x])
                temp = float(self.temperature[y, x])
                humid = float(self.humidity[y, x])
                pres = float(self.pressure[y, x])
                b = biome_from_env(elev, temp, humid, pres)
                self.biome_map[y, x] = mapping[b]

    def get_biome_at(self, x: int, y: int) -> Biome:
        """Return Biome enum at tile coordinates (x,y)."""
        h, w = self.biome_map.shape
        if x < 0 or x >= w or y < 0 or y >= h:
            return Biome.OCEAN
        idx = int(self.biome_map[y, x])
        return list(Biome)[idx]

    def color_map(self) -> np.ndarray:
        """Return an (h,w,3) uint8 color image of the biome map for rendering."""
        h, w = self.biome_map.shape
        img = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            for x in range(w):
                b = self.get_biome_at(x, y)
                img[y, x] = color_for_biome(b)
        return img

    def save_snapshot(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savez_compressed(path, elevation=self.elevation, temperature=self.temperature, humidity=self.humidity, pressure=self.pressure, biome=self.biome_map)

    def load_snapshot(self, path: str):
        data = np.load(path)
        self.elevation = data["elevation"]
        self.temperature = data["temperature"]
        self.humidity = data["humidity"]
        self.pressure = data["pressure"]
        self.biome_map = data.get("biome")
        self._loaded = True
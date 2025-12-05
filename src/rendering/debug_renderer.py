# --------------------------------------------------------
# File: src/rendering/debug_renderer.py
"""
Very small headless/debug renderer that prints basic stats to console every tick.
Useful for testing without Arcade.
"""
import time


class DebugRenderer:
    def __init__(self, world, pixel_manager):
        self.world = world
        self.pixels = pixel_manager
        self.running = True

    def run(self, ticks: int = 100, dt: float = 1.0):
        for t in range(ticks):
            alive = sum(1 for i in range(self.pixels.count) if self.pixels.alive[i])
            print(f"Tick {t:04d} | Pixels: {self.pixels.count} | Alive: {alive}")
            self.pixels.step(dt, self.world, getattr(self.world, 'resource_grid', None))
            time.sleep(0.05)


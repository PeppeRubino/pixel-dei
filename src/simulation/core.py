# -------------------------------------------------
# File: src/simulation/core.py
#
# Core simulation loop, decoupled from any GUI framework.
# It advances the World and PixelManager and exposes a
# lightweight snapshot interface for renderers / UIs.
# -------------------------------------------------

from typing import Optional, Dict, Any

from .metrics import RunRecorder


class Simulation:
    def __init__(self, world, pixel_manager, resource_grid: Optional[object] = None):
        """
        Parameters
        ----------
        world : world.world.World
            The global world instance (map, biomes, gases, etc.).
        pixel_manager : pixel.pixel_manager.PixelManager
            The manager that holds and updates all pixels.
        resource_grid : optional
            Optional grid of atoms/resources attached to the world.
        """
        self.world = world
        self.pixels = pixel_manager
        self.resource_grid = resource_grid

        # optional metrics recorder (can be attached by callers)
        self.metrics: Optional[RunRecorder] = None

        # simulation time in arbitrary units (ticks or seconds)
        self.time: float = 0.0
        # base time step used by UI-driven loops
        self.base_dt: float = 1.0 / 60.0
        # control flags
        self.paused: bool = False
        self.speed: float = 1.0  # 1.0x, 2.0x, etc.

    # -------------------------------------------------
    # MAIN STEP
    # -------------------------------------------------

    def step(self, dt: Optional[float] = None) -> None:
        """Advance the simulation by dt (scaled by self.speed).

        This is intentionally thin: most logic lives in World/PixelManager.
        """
        if self.paused:
            return

        if dt is None:
            dt = self.base_dt

        eff_dt = float(dt) * float(self.speed)

        # PixelManager.step already calls world.advance_environment when present,
        # so we simply delegate here.
        self.pixels.step(eff_dt, self.world, self.resource_grid)
        self.time += eff_dt

        if self.metrics is not None:
            try:
                self.metrics.update(self, eff_dt)
            except Exception:
                # Metrics collection must never break the main simulation loop.
                pass

    # -------------------------------------------------
    # SNAPSHOT FOR RENDERERS
    # -------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a lightweight view of the current state.

        Renderers should treat this as read-only and avoid mutating
        World/PixelManager directly.
        """
        return {
            "time": self.time,
            "world": self.world,
            "pixels": self.pixels,
            "resource_grid": self.resource_grid,
            "paused": self.paused,
            "speed": self.speed,
        }

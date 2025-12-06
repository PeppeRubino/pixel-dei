# File: src/main.py
"""
Entry point for the Evolutive Simulator.
Run this file from the `src/` directory:

    python main.py --pixels 500 --map data/maps/world.npz

It will:
  - create or load a World
  - create a ResourceGrid and attach it to the world
  - create a PixelManager and spawn pixels randomly
  - launch the Arcade GUI renderer (or a debug headless renderer with --headless)

This script is intentionally lightweight: most behaviour lives in the modules under
`world/` and `pixel/`.
"""
import os
import sys
import argparse

# ensure src/ is on sys.path when running main from within src/
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from world.world import World
from world.resources import ResourceGrid
from pixel.pixel_manager import PixelManager
from simulation.core import Simulation

# optional headless renderer
try:
    from rendering.debug_renderer import DebugRenderer
except Exception:
    DebugRenderer = None

# DearPyGui GUI
try:
    from gui.dpg_app import run_dpg_app
except Exception:
    run_dpg_app = None


def build_args():
    p = argparse.ArgumentParser("Evolutive Simulator Launcher")
    p.add_argument("--map", default=None, help="Path to saved map npz (optional)")
    p.add_argument("--pixels", type=int, default=300, help="Number of initial pixels to spawn")
    p.add_argument(
    "--size",
    type=int,
    nargs=2,
    default=[1024, 512],   # GLOBO REALE 2:1
    help="Map size: width height (global)"
)

    p.add_argument("--seed", type=int, default=0, help="Random seed for generator")
    p.add_argument("--tile-size", type=int, default=4, help="Tile size in pixels for rendering")
    p.add_argument("--headless", action="store_true", help="Run headless debug renderer instead of GUI")
    return p.parse_args()


def ensure_map_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def main():
    args = build_args()
    np_seed = args.seed

    if np_seed is not None:
        import numpy as _np

        _np.random.seed(np_seed)

    size = (int(args.size[0]), int(args.size[1]))

    print("[main] Creating world size=%s seed=%s" % (size, args.seed))
    world = World(size=size, seed=args.seed, map_path=args.map)

    # attach resource grid (atoms) to world
    print("[main] Creating resource grid")
    resource_grid = ResourceGrid(shape=(size[1], size[0]), initial_counts=8)
    world.resource_grid = resource_grid

    # pixel manager
    print("[main] Creating PixelManager")
    pm = PixelManager(capacity=max(1024, args.pixels * 4))
    print(f"[main] Spawning {args.pixels} pixels...")
    pm.spawn_random(world, resource_grid, n=args.pixels, species_prefix="Spec")

    # choose renderer
    if args.headless:
        if DebugRenderer is None:
            print("[main] No debug renderer available. Exiting.")
            return
        print("[main] Launching headless debug renderer")
        dbg = DebugRenderer(world, pm)
        dbg.run(ticks=1000, dt=1.0)
        return

    # GUI: DearPyGui-based single window
    sim = Simulation(world, pm, resource_grid)
    if run_dpg_app is None:
        print("[main] DearPyGui GUI is not available. Ensure dearpygui is installed.")
        return

    print("[main] Launching DearPyGui renderer (GUI)")
    run_dpg_app(sim)



if __name__ == "__main__":
    main()

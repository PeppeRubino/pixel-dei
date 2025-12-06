"""
Thin orchestration module for the DearPyGui-based GUI.

La logica è suddivisa in tre mixin:
  - TopBarMixin    (barra superiore: play/pausa/tempo/salvataggio)
  - WorldViewMixin (mappa biomi + pixel, zoom/pan, selezione)
  - SidebarMixin   (stato globale, pixel selezionato, log evolutivo)
"""
from typing import Deque, Tuple, Optional
from collections import deque
import time

import numpy as np
import dearpygui.dearpygui as dpg

from simulation.core import Simulation
from .dpg_constants import WINDOW_W, WINDOW_H
from .dpg_topbar import TopBarMixin
from .dpg_world_view import WorldViewMixin
from .dpg_sidebar import SidebarMixin


class DPGApp(TopBarMixin, WorldViewMixin, SidebarMixin):
    def __init__(self, sim: Simulation):
        self.sim = sim
        self.world = sim.world
        self.pm = sim.pixels
        self.texture_w = self.world.size[0]
        self.texture_h = self.world.size[1]

        # camera / view window in world coordinates
        w, h = self.world.size
        self.view_x0 = 0.0
        self.view_y0 = 0.0
        self.view_x1 = float(max(1, w - 1))
        self.view_y1 = float(max(1, h - 1))
        self._last_pan_pos: Optional[Tuple[float, float]] = None

        # histories for plots / stats
        self.pop_history: Deque[float] = deque(maxlen=200)
        self.evo_log: Deque[str] = deque(maxlen=6)

        self.last_alive: Optional[int] = None
        self.avg_energy: float = 0.0
        self.avg_stress: float = 0.0
        self.trait_diversity: int = 0
        self.avg_traits_per_cell: float = 0.0

        self.selected_pixel: Optional[int] = None

        self._last_time = time.time()

    # -------------------------------------------------
    # UI BUILD
    # -------------------------------------------------

    def build(self):
        dpg.create_context()
        dpg.create_viewport(title="Evolutive Simulator", width=WINDOW_W, height=WINDOW_H)

        # texture registry
        with dpg.texture_registry(show=False):
            dpg.add_dynamic_texture(
                self.texture_w,
                self.texture_h,
                self._world_color_map_rgba(),
                tag="world_texture",
            )

        # compose UI
        self._build_top_bar()
        self._build_world_window()
        self._build_sidebar()

        # mouse handlers per interazione con il mondo
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=self._on_mouse_click)
            try:
                dpg.add_mouse_wheel_handler(callback=self._on_mouse_wheel)
            except Exception:
                pass
            try:
                dpg.add_mouse_drag_handler(button=0, callback=self._on_mouse_drag)
            except Exception:
                pass

        dpg.setup_dearpygui()
        dpg.show_viewport()

    # -------------------------------------------------
    # FRAME LOOP
    # -------------------------------------------------

    def _on_frame(self):
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        # advance simulation
        self.sim.step(dt)

        # update world texture only if biomes changed
        if getattr(self.world, "_biome_dirty", False):
            dpg.set_value("world_texture", self._world_color_map_rgba())
            setattr(self.world, "_biome_dirty", False)

        # update stats e UI
        self._update_stats()
        self._update_world_drawlist()
        self._update_sidebar()


def run_dpg_app(sim: Simulation):
    app = DPGApp(sim)
    app.build()
    while dpg.is_dearpygui_running():
        app._on_frame()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()


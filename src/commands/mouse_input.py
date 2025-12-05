# commands/mouse_input.py
import math
import arcade
from typing import Tuple, Optional

class MouseInputHandler:
    """
    Gestisce gli eventi mouse/keyboard e applica le azioni sul renderer.
    Il renderer passato deve esporre:
      - offset_x, offset_y, scale, tile_size
      - selected_pixel, selected_biome, pixels, world
      - btn_start, btn_reset
      - metodi: _is_over_ui(x,y), _clamp_offsets()
    """

    def __init__(self, renderer):
        self.r = renderer
        # stato locale per il drag/click
        self.drag_start_mouse: Tuple[float, float] = (0.0, 0.0)
        self.drag_start_offset: Tuple[float, float] = (0.0, 0.0)
        self.dragging: bool = False
        self.mouse_down: bool = False
        self._press_button: Optional[int] = None
        self._press_world_pos: Optional[Tuple[float, float]] = None
        self.drag_threshold = 4  # px prima di considerare drag

    # ----------------- mouse press -----------------
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.drag_start_mouse = (x, y)
        self.drag_start_offset = (self.r.offset_x, self.r.offset_y)
        self.mouse_down = True
        self.dragging = False
        self._press_button = button
        self._press_world_pos = (self.r.offset_x + (x / (self.r.tile_size * self.r.scale)),
                                 self.r.offset_y + (y / (self.r.tile_size * self.r.scale)))

        # UI handling
        if self.r._is_over_ui(x, y):
            # bottoni
            if self.r.btn_start.contains(x, y):
                self.r.paused = not self.r.paused
                return
            if self.r.btn_reset.contains(x, y):
                try:
                    self.r.pixels.count = 0
                    self.r.pixels.spawn_random(self.r.world, None, n=200)
                except Exception as e:
                    print("[input] reset error:", e)
                return
            # click sui pannelli -> consumato
            return

        # Se vuoi drag immediato al press, abilita qui:
        # if button == arcade.MOUSE_BUTTON_LEFT:
        #     self.dragging = True

    # ----------------- mouse drag -----------------
    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int):
        # se siamo sopra la UI, non pannare
        if self.r._is_over_ui(x, y):
            return

        # Start drag only if movement exceeds threshold
        if not self.dragging:
            sx, sy = self.drag_start_mouse
            if math.hypot(x - sx, y - sy) >= self.drag_threshold:
                self.dragging = True

        if self.dragging and (buttons & arcade.MOUSE_BUTTON_LEFT):
            # convert screen delta to world tile delta
            dtx = -dx / (self.r.tile_size * self.r.scale)
            dty = -dy / (self.r.tile_size * self.r.scale)
            self.r.offset_x += dtx
            self.r.offset_y += dty
            self.r._clamp_offsets()
            # cancel selection while dragging
            self.r.selected_pixel = None

    # ----------------- mouse release -----------------
    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):
        self.mouse_down = False

        # se eravamo in drag, fermiamolo e non interpretare come click
        if self.dragging:
            self.dragging = False
            return

        # se il rilascio è dentro UI, nulla da fare
        if self.r._is_over_ui(x, y):
            return

        # altrimenti è un click (nessun drag)
        if self._press_button == arcade.MOUSE_BUTTON_LEFT:
            world_x = self.r.offset_x + (x / (self.r.tile_size * self.r.scale))
            world_y = self.r.offset_y + (y / (self.r.tile_size * self.r.scale))
            pid = self.r.pixels.find_nearest(world_x, world_y, radius=2.0)
            if pid is not None:
                self.r.selected_pixel = pid
                return
            else:
                self.r.selected_pixel = None
            bx = int(math.floor(world_x))
            by = int(math.floor(world_y))
            self.r.selected_biome = self.r.world.get_biome_at(bx, by)

    # ----------------- scroll (zoom) -----------------
    def on_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float):
        # ignore if over UI
        if self.r._is_over_ui(x, y):
            return

        zoom_step = 1.1
        factor = zoom_step ** scroll_y
        old_scale = self.r.scale
        new_scale = old_scale * factor
        new_scale = max(0.1, min(4.0, new_scale))
        if abs(new_scale - old_scale) < 1e-6:
            return

        # mantieni la posizione del mouse stabile nel mondo (zoom verso mouse)
        mouse_wx = self.r.offset_x + (x / (self.r.tile_size * old_scale))
        mouse_wy = self.r.offset_y + (y / (self.r.tile_size * old_scale))
        self.r.scale = new_scale
        self.r.offset_x = mouse_wx - (x / (self.r.tile_size * self.r.scale))
        self.r.offset_y = mouse_wy - (y / (self.r.tile_size * self.r.scale))
        self.r._clamp_offsets()

    # ----------------- keyboard -----------------
    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.SPACE:
            self.r.paused = not self.r.paused
        elif symbol in (arcade.key.PLUS, arcade.key.EQUAL):
            self.r.scale = min(4.0, self.r.scale * 1.1)
            self.r._clamp_offsets()
        elif symbol == arcade.key.MINUS:
            self.r.scale = max(0.1, self.r.scale / 1.1)
            self.r._clamp_offsets()
        elif symbol == arcade.key.R:
            self.r.pixels.count = 0
            self.r.pixels.spawn_random(self.r.world, None, n=200)


# --------------------------------------------------------
# File: src/ui/input.py
"""
Input helpers & simple button areas.
Previously used by the old Arcade renderer; can be reused by future GUI layers.
"""
from typing import Tuple


class Button:
    def __init__(self, x: float, y: float, w: float, h: float, label: str):
        self.rect = (x, y, w, h)
        self.label = label

    def contains(self, sx: float, sy: float) -> bool:
        x, y, w, h = self.rect
        return sx >= x and sx <= x + w and sy >= y and sy <= y + h



# --------------------------------------------------------
# File: src/ui/input.py
"""
Input helpers & simple button areas. The arcade renderer will use these
for hover/click detection on UI elements.
"""
from typing import Tuple


class Button:
    def __init__(self, x: float, y: float, w: float, h: float, label: str):
        self.rect = (x, y, w, h)
        self.label = label

    def contains(self, sx: float, sy: float) -> bool:
        x, y, w, h = self.rect
        return sx >= x and sx <= x + w and sy >= y and sy <= y + h


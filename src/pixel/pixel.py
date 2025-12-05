# src/pixel/pixel.py
"""
Simple Pixel data holder. In the full simulation Pixels will be managed
by PixelManager and stored in vectorized arrays, but a small class is
useful for debugging, serialization, and tests.
"""
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class Pixel:
    id: int
    species: str
    x: float
    y: float
    energy: float = 1.0
    stamina: float = 1.0
    alive: bool = True
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "id": int(self.id),
            "species": str(self.species),
            "x": float(self.x),
            "y": float(self.y),
            "energy": float(self.energy),
            "stamina": float(self.stamina),
            "alive": bool(self.alive),
            "metadata": self.metadata or {},
        }










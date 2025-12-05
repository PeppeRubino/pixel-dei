# -------------------------------------------------
# src/pixel/genome.py
"""
Placeholder genome module.
Real implementation will contain genome representation, mutation
and similarity measures. For now we expose a minimal Genome class
and a similarity function used by PixelManager if present.
"""
from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass
class Genome:
    data: Any


def random_genome(length: int = 8):
    # simple float vector genome
    return Genome(data=np.random.rand(length).astype(float))


def similarity(g1: Genome, g2: Genome) -> float:
    """Return similarity in range 0..1 (1 = identical).
    If genomes are incompatible types, fallback to 0.0.
    """
    try:
        a = np.asarray(g1.data, dtype=float)
        b = np.asarray(g2.data, dtype=float)
        if a.shape != b.shape:
            return 0.0
        # cosine similarity or 1 - normalized L2
        d = np.linalg.norm(a - b)
        maxd = np.linalg.norm(np.ones_like(a)) * np.sqrt(2)
        sim = 1.0 - (d / (d + 1e-9))
        return float(np.clip(sim, 0.0, 1.0))
    except Exception:
        return 0.0
# -------------------------------------------------
# src/pixel/reproduction.py
"""
Placeholder reproduction rules. The real system will produce a child genome
and possibly a new species name. Here we provide a simple function used by
PixelManager when two pixels mate.
"""
from typing import Tuple


def can_reproduce(similarity_score: float, threshold: float = 0.9) -> bool:
    return similarity_score >= threshold


def reproduce_simple(parent_a_genome, parent_b_genome):
    """
    Simple recombination: average genomes (assumes numeric arrays/lists).
    Returns child_genome, child_species_name
    """
    try:
        import numpy as np

        a = np.asarray(parent_a_genome.data, dtype=float)
        b = np.asarray(parent_b_genome.data, dtype=float)
        # equalize shapes by padding with zeros if needed
        if a.shape != b.shape:
            m = max(a.size, b.size)
            a = np.resize(a, m)
            b = np.resize(b, m)
        child = (a + b) / 2.0
        # small mutation (commented out for now)
        # child += np.random.normal(scale=0.01, size=child.shape)
        from pixel.genome import Genome

        child_genome = Genome(data=child)
        child_species = "hybrid"
        return child_genome, child_species
    except Exception:
        return None, "unknown"

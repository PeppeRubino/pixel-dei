# -------------------------------------------------
# src/pixel/reproduction.py
"""
Reproduction rules.

Phase 1: only asexual 1 -> 2 reproduction exists, and even that is rare
and metabolically expensive. Sexual recombination helpers are kept for
future phases but are not used by default.
"""
from typing import Tuple

import numpy as np


# Index in the genome vector that encodes basic replication machinery.
REPLICATION_GENE_INDEX = 0
REPLICATION_GENE_THRESHOLD = 0.7

# Division thresholds over internal resources (see pixel.metabolism)
DIV_ENERGY = 0.7
DIV_ORGANICS = 0.6
DIV_MEMBRANE = 0.5
DIV_INFO = 0.2


def has_basic_replication(genome) -> bool:
    """Return True if genome encodes basic 1->2 division machinery."""
    try:
        g = np.asarray(getattr(genome, "data", []), dtype=float).ravel()
        if g.size == 0:
            return False
        return bool(g[REPLICATION_GENE_INDEX] >= REPLICATION_GENE_THRESHOLD)
    except Exception:
        return False


def division_conditions_met(stocks, idx_energy: int, idx_org: int, idx_mem: int, idx_info: int) -> bool:
    """Check minimal internal-resource thresholds for attempting division."""
    if stocks[idx_energy] <= DIV_ENERGY:
        return False
    if stocks[idx_org] <= DIV_ORGANICS:
        return False
    if stocks[idx_mem] <= DIV_MEMBRANE:
        return False
    if stocks[idx_info] <= DIV_INFO:
        return False
    return True


def asexual_clone_genome(parent_genome):
    """Return a child genome as a mostly faithful copy with small noise."""
    from pixel.genome import Genome

    try:
        data = np.asarray(parent_genome.data, dtype=float)
        # small Gaussian mutation
        mutated = data + np.random.normal(scale=0.01, size=data.shape)
        return Genome(data=mutated)
    except Exception:
        return parent_genome


# --- Sexual helpers reserved for future phases ---

def can_reproduce(similarity_score: float, threshold: float = 0.9) -> bool:
    return similarity_score >= threshold


def reproduce_simple(parent_a_genome, parent_b_genome):
    """
    Simple recombination: average genomes (assumes numeric arrays/lists).
    Returns child_genome, child_species_name
    """
    try:
        a = np.asarray(parent_a_genome.data, dtype=float)
        b = np.asarray(parent_b_genome.data, dtype=float)
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

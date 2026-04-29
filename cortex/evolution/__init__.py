"""
cortex.evolution
=================
M13.1 + M14.2 — Moduli di auto-evoluzione di SPEACE.

Espone:
  CodeMutationLab        — auto-modifica Python con AST + rollback (M13.1)
  MutationProposal       — proposta da approvare via SafeProactive
  MutationEvent          — record di una mutazione applicata
  MutationType           — enum tipi di mutazione
  MutationRiskLevel      — LOW / MEDIUM
  EvolutionaryAlgorithm  — GA reale: population + crossover + selection (M14.2)
  Individual             — individuo GA (genome dict, fitness, generation)
  EvolutionaryResult     — risultato di una run evolutiva
  load_epigenome_genome_slice — carica base_genome da epigenome.yaml
"""

from .code_mutation_lab import (
    CodeMutationLab,
    MutationProposal,
    MutationEvent,
    MutationType,
    MutationRiskLevel,
)

from .evolutionary_algorithm import (
    EvolutionaryAlgorithm,
    Individual,
    EvolutionaryResult,
    load_epigenome_genome_slice,
    DEFAULT_FITNESS_WEIGHTS,
    FITNESS_EXCELLENT,
    FITNESS_MIN_TO_APPLY,
)

__all__ = [
    "CodeMutationLab",
    "MutationProposal",
    "MutationEvent",
    "MutationType",
    "MutationRiskLevel",
    "EvolutionaryAlgorithm",
    "Individual",
    "EvolutionaryResult",
    "load_epigenome_genome_slice",
    "DEFAULT_FITNESS_WEIGHTS",
    "FITNESS_EXCELLENT",
    "FITNESS_MIN_TO_APPLY",
]

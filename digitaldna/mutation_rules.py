"""
DigitalDNA Mutation Rules - Mutazioni Epigenetiche Automatiche
"""

from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def apply_epigenetic_mutation(mutation_type: str, context: dict) -> Dict[str, Any]:
    """
    Applica mutazione all'epigenome basata su Learning Core metrics.

    Args:
        mutation_type: "positive" | "negative" | "neutral"
        context: dict con c_index, fitness, ecc.

    Returns:
        Dict con tipo mutazione e parametri modificati
    """
    timestamp = datetime.now().isoformat()

    if mutation_type == "positive":
        mutation = {
            "type": "positive_epigenetic",
            "timestamp": timestamp,
            "effects": {
                "learning_rate": "+0.05",
                "push_intensity": "+0.02",
                "curiosity": "+0.03"
            },
            "triggered_by": context.get("c_index", 0),
            "status": "applied"
        }
        logger.info(f"🧬 Mutazione positiva applicata: C-index trigger={context.get('c_index')}")

    elif mutation_type == "negative":
        mutation = {
            "type": "negative_epigenetic",
            "timestamp": timestamp,
            "effects": {
                "learning_rate": "-0.02",
                "stability": "+0.05"
            },
            "triggered_by": context.get("c_index", 0),
            "status": "applied"
        }
        logger.info(f"🧬 Mutazione negativa applicata: stabilizzazione sistema")

    else:
        mutation = {
            "type": "neutral_exploration",
            "timestamp": timestamp,
            "effects": {
                "curiosity": "+0.01",
                "exploration_bias": "+0.02"
            },
            "status": "applied"
        }
        logger.info(f"🧬 Mutazione esplorativa applicata")

    return mutation


def evaluate_mutation_impact(before: Dict, after: Dict) -> float:
    """
    Valuta l'impatto di una mutazione sulle performance.

    Args:
        before: metriche pre-mutazione
        after: metriche post-mutazione

    Returns:
        Score di impatto (-1.0 a 1.0)
    """
    c_before = before.get("c_index", 0.7)
    c_after = after.get("c_index", 0.7)
    f_before = before.get("fitness", 0.7)
    f_after = after.get("fitness", 0.7)

    c_delta = (c_after - c_before) / c_before if c_before > 0 else 0
    f_delta = (f_after - f_before) / f_before if f_before > 0 else 0

    impact = (c_delta * 0.6) + (f_delta * 0.4)
    return max(-1.0, min(1.0, impact))
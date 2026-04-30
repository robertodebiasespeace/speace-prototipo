"""
cortex.cognitive_autonomy.predictive
=====================================
M10.1 — Predictive Coding: il cervello come macchina predittiva.

Principio (Karl Friston, Free Energy Principle):
  Il cervello non elabora la realtà come arriva — genera continuamente
  PREVISIONI su cosa arriverà, e trasmette al Cortex solo gli ERRORI
  di previsione (prediction error = reale - atteso).

  Quasi tutto ciò che "percepiamo" è già "compilato" da modelli interni.
  Solo le discrepanze rispetto alle previsioni emergono come segnale nuovo.

Effetto pratico per SPEACE:
  - In condizioni stabili: 60-80% dei segnali vengono soppressi (già previsti)
  - Solo eventi genuinamente NUOVI o INATTESI attivano il Cortex
  - Riduzione drastica del carico computazionale
  - Reattività aumentata a eventi inaspettati (prediction error alto)

Componenti:
  PredictionModel  — modello interno dello stato atteso (da storia recente)
  PredictionError  — calcola e classifica l'errore di previsione
  PredictiveProcessor — filtra i segnali in ingresso al Cortex

EPI-012: cognitive_autonomy.predictive.enabled = true
M10.1 | 2026-04-28
"""

from .predictive_processor import (
    PredictionModel,
    PredictionError,
    PredictionErrorLevel,
    PredictiveProcessor,
    BehavioralPredictor,
    BehavioralPrediction,
)

__all__ = [
    "PredictionModel",
    "PredictionError",
    "PredictionErrorLevel",
    "PredictiveProcessor",
    "BehavioralPredictor",
    "BehavioralPrediction",
]

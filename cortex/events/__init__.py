"""
cortex.events
==============
M10.3 — Event-Driven Signaling: dal polling all'architettura a eventi.

Principio biologico:
  Il sistema nervoso non fa "polling" continuo — risponde a EVENTI
  (potenziali d'azione). La trasmissione avviene solo quando il segnale
  supera la soglia di attivazione. Risparmio energetico enorme rispetto
  al polling periodico.

Principio fisico associato (risonanza orbitale):
  Gli heartbeat dei processi SPEACE devono evitare allineamento simultaneo
  (spike di carico). Il ResonanceScheduler calcola offset che minimizzano
  la probabilità di esecuzione contemporanea di processi pesanti.

Componenti:
  EventType         — tassonomia degli eventi SPEACE
  SPEACEEvent       — evento singolo (immutabile, serializzabile)
  EventBus          — pub/sub in-process (threading + queue, no deps esterne)
  ResonanceScheduler — calcola intervalli anti-risonanza per i processi

EPI-012 / M10.3 | 2026-04-28
"""

from .event_bus import EventType, SPEACEEvent, EventBus
from .resonance  import ResonanceScheduler, ProcessSpec, ResonanceSchedule

__all__ = [
    "EventType",
    "SPEACEEvent",
    "EventBus",
    "ResonanceScheduler",
    "ProcessSpec",
    "ResonanceSchedule",
]

"""
cortex.events.event_bus
========================
M10.3 — EventBus: pub/sub in-process per SPEACE.

Sostituisce il polling periodico tra moduli con un'architettura a eventi:
i moduli non interrogano periodicamente lo stato degli altri — ricevono
notifiche solo quando qualcosa cambia (principio del potenziale d'azione).

Implementazione:
  - Thread-safe, zero dipendenze esterne (solo stdlib: threading, queue)
  - Delivery sincrona (nel thread del publisher) o asincrona (thread dedicato)
  - Subscriber per tipo di evento (filtro preciso) o wildcard (tutti gli eventi)
  - Dead letter queue per eventi non consegnati (log, no crash)
  - Metriche: eventi pubblicati, consegnati, dropped, latenza media

Tipi di evento (EventType) - ispirati ai segnali neurochimici biologici:
  VIABILITY_ALERT       ← dopamina/adrenalina: segnale di pericolo/urgenza
  CURIOSITY_SPIKE       ← dopamina: segnale di novità/reward
  THREAT_DETECTED       ← cortisolo: risposta immunitaria
  MEMORY_CONSOLIDATED   ← acetilcolina: consolidamento notturno
  REPAIR_STARTED        ← citochine: inizio riparazione
  REPAIR_ENDED          ← serotonina: risoluzione stress
  MUTATION_PROPOSED     ← segnale evolutivo
  ENERGY_LOW            ← glucosio basso: avviso risparmio energetico
  PREDICTION_ERROR_HIGH ← errore predittivo elevato: novità rilevante
  CYCLE_COMPLETED       ← battito cardiaco: ciclo SMFOI completato

M10.3 | 2026-04-28
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("speace.events.bus")


# ─────────────────────────────────────────────────────────────────────────────
# EventType — tassonomia degli eventi SPEACE
# ─────────────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    # Omeostatici (urgenza)
    VIABILITY_ALERT       = "viability_alert"
    ENERGY_LOW            = "energy_low"
    REPAIR_STARTED        = "repair_started"
    REPAIR_ENDED          = "repair_ended"

    # Cognitivi (apprendimento/novità)
    CURIOSITY_SPIKE       = "curiosity_spike"
    PREDICTION_ERROR_HIGH = "prediction_error_high"
    MEMORY_CONSOLIDATED   = "memory_consolidated"

    # Sicurezza / immunitari
    THREAT_DETECTED       = "threat_detected"

    # Evolutivi
    MUTATION_PROPOSED     = "mutation_proposed"
    MUTATION_APPLIED      = "mutation_applied"

    # Ciclo
    CYCLE_COMPLETED       = "cycle_completed"

    # Wildcard (ascolta tutti)
    WILDCARD              = "*"


# ─────────────────────────────────────────────────────────────────────────────
# SPEACEEvent — evento singolo (immutabile)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SPEACEEvent:
    """
    Evento SPEACE. Immutabile per garantire thread-safety senza lock.

    Attributi:
        event_type:  tipo dell'evento
        source:      nome del modulo/componente che ha generato l'evento
        payload:     dati dell'evento (qualsiasi tipo serializzabile)
        priority:    0 (massima) → 9 (minima). Default 5 (normale).
        event_id:    UUID generato automaticamente
        timestamp:   UNIX timestamp di creazione
    """
    event_type: EventType
    source:     str
    payload:    Any          = None
    priority:   int          = 5
    event_id:   str          = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp:  float        = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "source":     self.source,
            "priority":   self.priority,
            "timestamp":  self.timestamp,
            "payload":    str(self.payload)[:200] if self.payload else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# EventBus — pub/sub in-process
# ─────────────────────────────────────────────────────────────────────────────

# Tipo callback subscriber
SubscriberCallback = Callable[[SPEACEEvent], None]


class EventBus:
    """
    M10.3 — Bus eventi in-process per SPEACE.

    Architettura pub/sub thread-safe senza dipendenze esterne.
    Ispirato al Global Workspace Theory (Baars): un "workspace globale"
    dove i moduli specializzati trasmettono informazioni rilevanti
    all'intera architettura cognitiva.

    Modalità:
      SYNC  (default): il subscriber viene chiamato nel thread del publisher.
                       Più semplice, adatto a handler veloci.
      ASYNC:           gli eventi vengono messi in coda e consegnati
                       da un thread dedicato. Adatto a handler lenti.

    Uso base:
        bus = EventBus()

        # Iscrizione a un tipo specifico
        bus.subscribe(EventType.VIABILITY_ALERT, my_handler)

        # Iscrizione a tutti gli eventi
        bus.subscribe(EventType.WILDCARD, my_global_handler)

        # Pubblicazione
        bus.publish(SPEACEEvent(
            event_type=EventType.VIABILITY_ALERT,
            source="homeostatic_controller",
            payload={"viability": 0.25, "alerts": ["energy_critical"]},
            priority=1,
        ))

    Uso semplificato:
        bus.emit(EventType.VIABILITY_ALERT, source="homeostasis",
                 payload={"viability": 0.25})
    """

    def __init__(
        self,
        async_mode:   bool = False,
        queue_maxsize: int = 500,
    ) -> None:
        self._subscribers: Dict[str, List[SubscriberCallback]] = {}
        self._lock   = threading.RLock()
        self._async  = async_mode
        self._queue: Optional[queue.PriorityQueue] = None
        self._worker: Optional[threading.Thread]   = None
        self._running = False

        # Metriche
        self._published  = 0
        self._delivered  = 0
        self._dropped    = 0
        self._latencies: List[float] = []

        if async_mode:
            self._queue  = queue.PriorityQueue(maxsize=queue_maxsize)
            self._running = True
            self._worker  = threading.Thread(
                target=self._dispatch_loop,
                name="speace-eventbus",
                daemon=True,
            )
            self._worker.start()
            logger.info("[EventBus] Avviato in modalità ASYNC")

    # ── Pub/Sub API ──────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: EventType,
        callback:   SubscriberCallback,
    ) -> str:
        """
        Iscrive un callback a un tipo di evento.
        EventType.WILDCARD → riceve tutti gli eventi.

        Ritorna un subscription_id per eventuale unsubscribe.
        """
        key = event_type.value
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)
        logger.debug("[EventBus] subscribe: %s → %s", key, callback.__name__)
        return f"{key}::{id(callback)}"

    def unsubscribe(self, event_type: EventType, callback: SubscriberCallback) -> bool:
        """Rimuove un subscriber. Ritorna True se trovato e rimosso."""
        key = event_type.value
        with self._lock:
            subs = self._subscribers.get(key, [])
            if callback in subs:
                subs.remove(callback)
                return True
        return False

    def publish(self, event: SPEACEEvent) -> int:
        """
        Pubblica un evento. Ritorna il numero di subscriber notificati.
        In modalità SYNC: consegna immediata nel thread corrente.
        In modalità ASYNC: mette in coda (priority = event.priority).
        """
        self._published += 1

        if self._async and self._queue is not None:
            try:
                self._queue.put_nowait((event.priority, time.time(), event))
                return 0  # conteggio non immediato in async
            except queue.Full:
                self._dropped += 1
                logger.warning("[EventBus] Queue piena, evento droppato: %s", event.event_type)
                return 0

        return self._deliver(event)

    def emit(
        self,
        event_type: EventType,
        source:     str,
        payload:    Any  = None,
        priority:   int  = 5,
    ) -> int:
        """Shortcut: crea e pubblica un evento in un'unica chiamata."""
        return self.publish(SPEACEEvent(
            event_type=event_type,
            source=source,
            payload=payload,
            priority=priority,
        ))

    # ── Delivery ─────────────────────────────────────────────────────────────

    def _deliver(self, event: SPEACEEvent) -> int:
        """Consegna sincrona a tutti i subscriber rilevanti."""
        t0 = time.monotonic()
        count = 0

        with self._lock:
            # Subscriber specifici per tipo
            specific = list(self._subscribers.get(event.event_type.value, []))
            # Subscriber wildcard
            wildcards = list(self._subscribers.get(EventType.WILDCARD.value, []))

        for cb in specific + wildcards:
            try:
                cb(event)
                count += 1
                self._delivered += 1
            except Exception as e:
                logger.error(
                    "[EventBus] Errore in subscriber %s per %s: %s",
                    getattr(cb, "__name__", "?"), event.event_type.value, e
                )
                self._dropped += 1

        elapsed_ms = (time.monotonic() - t0) * 1000
        self._latencies.append(elapsed_ms)
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-500:]

        if count > 0:
            logger.debug(
                "[EventBus] %s → %d subscriber (%.2fms)",
                event.event_type.value, count, elapsed_ms
            )
        return count

    def _dispatch_loop(self) -> None:
        """Thread worker per modalità ASYNC."""
        while self._running:
            try:
                _, _, event = self._queue.get(timeout=0.5)
                self._deliver(event)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("[EventBus] dispatch_loop error: %s", e)

    def stop(self) -> None:
        """Ferma il thread async (se attivo)."""
        self._running = False
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=2.0)

    # ── Metriche ─────────────────────────────────────────────────────────────

    @property
    def mean_latency_ms(self) -> float:
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    def get_metrics(self) -> dict:
        with self._lock:
            n_subs = sum(len(v) for v in self._subscribers.values())
        return {
            "published":       self._published,
            "delivered":       self._delivered,
            "dropped":         self._dropped,
            "subscribers":     n_subs,
            "mean_latency_ms": round(self.mean_latency_ms, 3),
            "async_mode":      self._async,
            "queue_size":      self._queue.qsize() if self._queue else 0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Global bus singleton (opzionale — per chi preferisce un bus condiviso)
# ─────────────────────────────────────────────────────────────────────────────

_global_bus: Optional[EventBus] = None

def get_global_bus() -> EventBus:
    """Ritorna (o crea) il bus eventi globale di SPEACE."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


__all__ = ["EventType", "SPEACEEvent", "EventBus", "get_global_bus"]

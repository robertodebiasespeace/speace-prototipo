"""
SPEACE Cortex – Base Compartment
Classe astratta che ogni comparto del Cortex eredita.

Principio: il Cortex NON è 9 moduli indipendenti, è la dinamica tra di essi.
Ogni comparto riceve uno State (dict JSON) e restituisce uno State arricchito.

Gerarchia di controllo (level):
  1 = Controllo     (Prefrontal, Safety)    — Safety ha override assoluto
  2 = Cognizione    (Temporal, WorldModel, DMN)
  3 = Memoria       (Hippocampus)
  4 = Azione        (Parietal, Cerebellum)
  5 = Evoluzione    (Curiosity)

I comparti esistenti mantengono le loro API specifiche (plan, reflect, ecc.).
BaseCompartment aggiunge SOLO un metodo unificato `process(state)` per il
flusso neurale, senza toccare la logica esistente (backward compatible).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict

from cortex import state_bus


class BaseCompartment(ABC):
    """Classe astratta per ogni comparto del SPEACE Cortex."""

    # Sotto-classi devono definire questi attributi di classe
    name: str = "unnamed_compartment"
    level: int = 3  # default: memoria/cognizione neutra

    # Solo Safety può fare override assoluto del flusso
    _OVERRIDE_ALLOWED = False

    def can_override(self) -> bool:
        """True se questo comparto ha autorità di override sul flusso."""
        return self._OVERRIDE_ALLOWED

    def activation_gate(self, state: Dict[str, Any]) -> bool:
        """
        True se questo comparto deve processare lo state nel ciclo corrente.
        Default: attivo sempre. Sotto-classi possono condizionare l'attivazione.

        Il ConditionalScheduler può leggere questo gate per decidere
        se invocare o meno il comparto.
        """
        return True

    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa lo State e restituisce la versione arricchita.
        Deve essere side-effect free sullo state input (ritornare nuovo dict
        o lo stesso dopo mutazioni minime additive).
        Deve chiamare `state_bus.log_compartment(state, self.name, self.level)`
        almeno una volta.
        """
        raise NotImplementedError

    # -- Helper shortcut ------------------------------------------------

    def _log(self, state: Dict[str, Any], status: str = "ok", note: str = None) -> Dict[str, Any]:
        return state_bus.log_compartment(state, self.name, self.level, status=status, note=note)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} level={self.level}>"

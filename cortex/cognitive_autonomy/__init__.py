"""
SPEACE Cortex — Cognitive Autonomy (M5)

Decimo comparto Cortex e sottosistemi che chiudono i 6 gap identificati
dalla critica BRIGHT/attNA:

    GAP 1 — Omeostasi cognitiva       → homeostasis/
    GAP 2 — Motivazione endogena      → motivation/
    GAP 3 — Memoria autobiografica    → memory/
    GAP 4 — Loop sensoriomotorio      → attention/
    GAP 5 — Plasticità strutturale    → plasticity/
    GAP 6 — Vincoli intrinseci        → constraints/

STATO: M5.0 scaffold completato 2026-04-24 (proposta approvata
`PROP-COGNITIVE-AUTONOMY-M5`, scope full).

POLITICA DI ATTIVAZIONE
-----------------------
Tutti i moduli sono **default OFF**. L'abilitazione passa da
`digitaldna/epigenome.yaml → cognitive_autonomy.<subsystem>.enabled =
true` e richiede approvazione SafeProactive separata per ogni flag
OFF → ON. Questo vincolo è deliberato: M5 aggiunge un *layer di
autonomia*, non un layer *autonomamente attivo*.

L'esecuzione dei task M5.1+ è subordinata al closure di M4-CNM (M4.20).
M5.0 (questo scaffold) e M5.0.a (snapshot pre-esecuzione) sono
sbloccati immediatamente per permettere planning e revisione
architetturale in parallelo al completamento della mesh.

NIENTE SIDE-EFFECT ALL'IMPORT
-----------------------------
Coerentemente con Appendice F del documento ingegneristico, questo
package non importa dipendenze runtime eagerly. I sottopacchetti sono
caricati solo quando gli handler del Cortex li istanziano sulla base
dell'epigenoma.
"""

__all__ = [
    "homeostasis",
    "motivation",
    "memory",
    "attention",
    "plasticity",
    "constraints",
]

# Versione del layer. Bump a 0.2 alla chiusura M5A (homeostasi + coerenza),
# a 0.3 alla chiusura M5B (memoria autobiografica), a 1.0 a M5.20 con
# Cognitive Autonomy Score ≥ 4/6.
__version__ = "0.1.0-scaffold"

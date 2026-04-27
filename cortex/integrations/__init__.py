"""
SPEACE Cortex — External Integrations

Integrazioni opzionali (default OFF) con tool esterni che arricchiscono
comparti specifici del Cortex. Ogni integrazione è opt-in via
`digitaldna/epigenome.yaml → integrations.<name>.enabled = true`.

Moduli attuali:
    - obsidian_bridge : Hippocampus ↔ Obsidian vault (Local REST API)
    - hermes_adapter  : Memoria persistente FTS5 via Hermes Agent

Questi moduli NON devono essere importati eagerly da SPEACE-main.py: vengono
caricati solo quando l'epigenome li abilita.
"""

__all__ = ["obsidian_bridge", "hermes_adapter"]

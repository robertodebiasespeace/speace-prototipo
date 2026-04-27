"""
SPEACE Cortex — Obsidian Bridge (INT-OBS.1)

Bridge bidirezionale tra Hippocampus (memoria SPEACE) e un vault Obsidian
locale, attraverso il plugin community "Local REST API" di coddingtonbear
(https://github.com/coddingtonbear/obsidian-local-rest-api).

OBIETTIVO
---------
Rendere il vault Obsidian una vista navigabile ed editabile della memoria
SPEACE: le note episodiche, le proposte SafeProactive, i brief del Team
Scientifico e i log di ciclo SMFOI vengono proiettati come note Markdown
con metadati YAML, e le modifiche umane possono essere ri-assorbite dal
Hippocampus come input di apprendimento.

STATO
-----
SCAFFOLD (default OFF). L'integrazione è attiva solo se
`digitaldna/epigenome.yaml` contiene:

    integrations:
      obsidian:
        enabled: true
        vault_path: "C:/Users/rober/Documents/Obsidian/SPEACE"
        rest_api_port: 27123
        api_key: "<token-local-plugin>"

SICUREZZA
---------
- Il bridge usa SOLO il loopback (127.0.0.1). Nessuna esposizione di rete.
- Ogni scrittura in vault passa da `_write_safeproactive_check()` (stub
  per ora; verrà collegato a `safeproactive/` in INT-OBS.2).
- Lettura/scrittura limitate al `vault_path` configurato — niente path
  traversal.

TEST
----
Questo modulo deve essere importabile senza Obsidian e senza plugin
installati (nessun side-effect all'import). Un test futuro verificherà
che `ObsidianBridge(enabled=False).push_episode(...)` sia un no-op.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SPEACE.integrations.obsidian")


# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

@dataclass
class ObsidianConfig:
    """Configurazione caricata da `epigenome.yaml → integrations.obsidian`."""

    enabled: bool = False
    vault_path: Optional[str] = None
    rest_api_port: int = 27123
    api_key: Optional[str] = None
    # Cartelle di default dentro il vault
    folder_episodes: str = "SPEACE/Episodes"
    folder_proposals: str = "SPEACE/Proposals"
    folder_briefs: str = "SPEACE/Briefs"
    folder_cycle_logs: str = "SPEACE/Cycles"

    @classmethod
    def from_epigenome(cls, epigenome: Dict[str, Any]) -> "ObsidianConfig":
        node = (epigenome or {}).get("integrations", {}).get("obsidian", {})
        return cls(
            enabled=bool(node.get("enabled", False)),
            vault_path=node.get("vault_path"),
            rest_api_port=int(node.get("rest_api_port", 27123)),
            api_key=node.get("api_key"),
            folder_episodes=node.get("folder_episodes", "SPEACE/Episodes"),
            folder_proposals=node.get("folder_proposals", "SPEACE/Proposals"),
            folder_briefs=node.get("folder_briefs", "SPEACE/Briefs"),
            folder_cycle_logs=node.get("folder_cycle_logs", "SPEACE/Cycles"),
        )


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

@dataclass
class ObsidianBridge:
    """
    Ponte Hippocampus ↔ Obsidian.

    Quando `enabled=False` tutte le operazioni sono no-op sicure. Quando
    abilitato, usa il plugin Local REST API via HTTP su localhost.

    L'implementazione HTTP è lasciata volutamente stub: verrà completata in
    INT-OBS.2 con requests + test di integrazione. La scelta è segnalare
    l'intenzione architettonica senza introdurre una nuova dipendenza
    runtime finché l'integrazione non è approvata e abilitata.
    """

    config: ObsidianConfig = field(default_factory=ObsidianConfig)

    # ------------------------------------------------------------------ #
    # API pubblica
    # ------------------------------------------------------------------ #

    def push_episode(self, episode: Dict[str, Any]) -> bool:
        """
        Proietta un episodio autobiografico come nota Markdown nel vault.

        Schema `episode`:
            {
                "id": "ep-2026-04-24-0001",
                "timestamp": "2026-04-24T10:15:00",
                "c_index": 0.82,
                "cycle": 1042,
                "summary": "...",
                "tags": ["cycle", "reflection"],
            }
        """
        if not self.config.enabled:
            logger.debug("Obsidian bridge disabled — skip push_episode")
            return False
        note_path = self._note_path(self.config.folder_episodes, episode["id"])
        body = self._render_episode_md(episode)
        return self._write_note(note_path, body)

    def push_proposal(self, proposal: Dict[str, Any]) -> bool:
        """Proietta una proposta SafeProactive in `SPEACE/Proposals/`."""
        if not self.config.enabled:
            return False
        note_path = self._note_path(
            self.config.folder_proposals, proposal["id"]
        )
        body = self._render_proposal_md(proposal)
        return self._write_note(note_path, body)

    def pull_human_notes(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Legge note Markdown scritte da un umano nel vault (es. riflessioni,
        direttive orientative, annotazioni su proposte) e le restituisce
        come input per il Hippocampus / Default Mode Network.

        NON implementato (SCAFFOLD): ritorna [] finché INT-OBS.2 non lo
        collega al Local REST API.
        """
        if not self.config.enabled:
            return []
        logger.info("pull_human_notes: scaffold, return empty list")
        return []

    # ------------------------------------------------------------------ #
    # Interni
    # ------------------------------------------------------------------ #

    def _note_path(self, folder: str, note_id: str) -> Path:
        vault = Path(self.config.vault_path or "")
        return vault / folder / f"{note_id}.md"

    def _write_note(self, note_path: Path, body: str) -> bool:
        """
        SCAFFOLD: scrive su filesystem direttamente se il vault è montato
        localmente. In INT-OBS.2 verrà sostituito da chiamata HTTP al
        Local REST API plugin (così Obsidian può indicizzare live).
        """
        if not self._write_safeproactive_check(note_path, body):
            logger.warning("SafeProactive veto sulla scrittura in %s", note_path)
            return False
        try:
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(body, encoding="utf-8")
            logger.info("Obsidian: nota scritta in %s", note_path)
            return True
        except OSError as exc:
            logger.error("Obsidian write error: %s", exc)
            return False

    @staticmethod
    def _write_safeproactive_check(note_path: Path, body: str) -> bool:
        """
        Stub: in INT-OBS.2 genererà una proposta SafeProactive LOW per
        ogni scrittura con volume > soglia; per ora approva sempre.
        """
        _ = (note_path, body)
        return True

    @staticmethod
    def _render_episode_md(episode: Dict[str, Any]) -> str:
        ts = episode.get("timestamp", datetime.utcnow().isoformat())
        frontmatter = {
            "speace_type": "episode",
            "cycle": episode.get("cycle"),
            "c_index": episode.get("c_index"),
            "tags": episode.get("tags", []),
            "timestamp": ts,
        }
        return (
            "---\n"
            + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in frontmatter.items())
            + "\n---\n\n"
            + f"# {episode.get('id')}\n\n"
            + (episode.get("summary") or "")
            + "\n"
        )

    @staticmethod
    def _render_proposal_md(proposal: Dict[str, Any]) -> str:
        frontmatter = {
            "speace_type": "proposal",
            "risk_level": proposal.get("risk_level"),
            "status": proposal.get("status"),
            "timestamp": proposal.get("timestamp"),
        }
        return (
            "---\n"
            + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in frontmatter.items())
            + "\n---\n\n"
            + f"# {proposal.get('id')}\n\n"
            + (proposal.get("description") or "")
            + "\n"
        )


__all__ = ["ObsidianConfig", "ObsidianBridge"]

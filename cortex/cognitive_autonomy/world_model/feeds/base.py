"""
FeedConnector base class — M6.3

Interfaccia comune per tutti i connettori di dati esterni.
Tutti i connettori sono READ-ONLY e implementano:
  - fetch() → FeedResult (live HTTP oppure offline fixture)
  - offline fallback automatico se HTTP fallisce o timeout
  - rate limiting (min_interval_s)

Milestone: M6.3
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("speace.world_model.feeds")

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


@dataclass
class FeedResult:
    feed_name:  str
    status:     str                     # "ok" | "offline" | "error" | "cached"
    data:       Dict[str, Any] = field(default_factory=dict)
    source:     str = "live"            # "live" | "fixture" | "cache"
    ts:         Optional[str] = None
    error:      Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "cached")


class FeedConnector:
    """
    Base class per connettori di feed esterni read-only.

    Subclasses devono implementare:
      - _url() → str
      - _parse(raw: bytes) → Dict[str, Any]
      - _fixture() → Dict[str, Any]  (dati offline di fallback)
    """

    name: str = "base"
    min_interval_s: float = 300.0   # max 1 fetch ogni 5 min
    timeout_s: float = 8.0

    def __init__(self) -> None:
        self._last_fetch_ts: float = 0.0
        self._last_result: Optional[FeedResult] = None

    def fetch(self, force: bool = False) -> FeedResult:
        """
        Esegue il fetch del feed.
        Se il rate limit non è scaduto, ritorna l'ultimo risultato cached.
        Se il fetch HTTP fallisce, usa il fixture offline.
        """
        now = time.monotonic()
        # Rate limit — anche se l'ultima fetch era offline/fixture
        if not force and (now - self._last_fetch_ts) < self.min_interval_s:
            if self._last_result:
                r = FeedResult(
                    feed_name=self.name,
                    status="cached",
                    data=self._last_result.data,
                    source="cache",
                    ts=self._last_result.ts,
                )
                return r

        try:
            url = self._url()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SPEACE-WorldModel/1.0 (research; read-only)"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read()
            data = self._parse(raw)
            from datetime import datetime, timezone
            result = FeedResult(
                feed_name=self.name,
                status="ok",
                data=data,
                source="live",
                ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
            self._last_fetch_ts = now
            self._last_result = result
            logger.info("[%s] live fetch OK — %d keys", self.name, len(data))
            return result

        except Exception as e:
            logger.warning("[%s] fetch failed (%s), using fixture", self.name, e)
            fixture = self._fixture()
            from datetime import datetime, timezone
            result = FeedResult(
                feed_name=self.name,
                status="offline",
                data=fixture,
                source="fixture",
                ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error=str(e),
            )
            self._last_fetch_ts = now   # rate-limit anche dopo fallimento
            self._last_result = result
            return result

    def _url(self) -> str:
        raise NotImplementedError

    def _parse(self, raw: bytes) -> Dict[str, Any]:
        return json.loads(raw.decode("utf-8", errors="replace"))

    def _fixture(self) -> Dict[str, Any]:
        """Dati offline di fallback. Subclasses possono caricare da fixtures/."""
        fixture_path = _FIXTURES_DIR / f"{self.name}.json"
        if fixture_path.exists():
            try:
                return json.loads(fixture_path.read_text(encoding="utf-8"))
            except Exception:
                pass
  
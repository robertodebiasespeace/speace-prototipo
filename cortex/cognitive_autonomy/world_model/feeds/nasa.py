"""
NASA DONKI Feed — M6.3
Solar/space weather data via NASA DONKI API (DEMO_KEY, read-only).
Offline fixture: solar flare + CME data statica.
"""
from __future__ import annotations
import json
from typing import Any, Dict
from .base import FeedConnector

_NASA_API_KEY = "DEMO_KEY"   # public demo key, rate-limited

class NASADonkiFeed(FeedConnector):
    name = "nasa"
    min_interval_s = 600.0   # max 1 fetch ogni 10 min (DEMO_KEY limit)

    def _url(self) -> str:
        # Last 7 days of solar flare events
        from datetime import datetime, timedelta, timezone
        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        s = start.strftime("%Y-%m-%d")
        e = end.strftime("%Y-%m-%d")
        return (f"https://api.nasa.gov/DONKI/FLR"
                f"?startDate={s}&endDate={e}&api_key={_NASA_API_KEY}")

    def _parse(self, raw: bytes) -> Dict[str, Any]:
        events = json.loads(raw.decode("utf-8", errors="replace"))
        if not isinstance(events, list):
            events = []
        flares = []
        for ev in events[-10:]:   # last 10
            flares.append({
                "flr_id":     ev.get("flrID", "?"),
                "start_time": ev.get("beginTime", "?"),
                "peak_time":  ev.get("peakTime", "?"),
                "class":      ev.get("classType", "?"),
                "source":     ev.get("sourceLocation", "?"),
            })
        return {
            "solar_flares_7d": len(events),
            "last_flares":     flares,
            "data_source":     "NASA DONKI",
        }

    def _fixture(self) -> Dict[str, Any]:
        return {
            "solar_flares_7d": 3,
            "last_flares": [
                {"flr_id": "2026-04-20T06:30:00-FLR-001",
                 "start_time": "2026-04-20T06:30Z", "peak_time": "2026-04-20T06:45Z",
                 "class": "M1.5", "source": "N22W35"},
                {"flr_id": "2026-04-22T14:10:00-FLR-002",
                 "start_time": "2026-04-22T14:10Z", "peak_time": "2026-04-22T14:22Z",
                 "class": "C8.2", "source": "S05E10"},
            ],
            "data_source": "NASA DONKI (fixture/offline)",
        }

__all__ = ["NASADonkiFeed"]

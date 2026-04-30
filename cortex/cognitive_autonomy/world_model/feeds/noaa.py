"""
NOAA Climate Feed — M6.3
CO2 data via NOAA GML Mauna Loa (public JSON endpoint, read-only).
Offline fixture: CO2 ppm + temperatura anomalia.
"""
from __future__ import annotations
import json
from typing import Any, Dict
from .base import FeedConnector


class NOAAClimateFeed(FeedConnector):
    name = "noaa"
    min_interval_s = 3600.0   # max 1 fetch/ora

    def _url(self) -> str:
        # NOAA GML CO2 monthly mean (Mauna Loa) — public JSON
        return "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.json"

    def _parse(self, raw: bytes) -> Dict[str, Any]:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        # NOAA JSON: {"description":..., "data":[{"year":..,"month":..,"average":..}, ...]}
        records = data.get("data", [])
        if not records:
            return self._fixture()
        latest = records[-1]
        trend  = None
        if len(records) >= 13:
            prev_year = records[-13]
            trend = round(latest.get("average", 0) - prev_year.get("average", 0), 2)
        return {
            "co2_ppm":          latest.get("average"),
            "co2_year":         latest.get("year"),
            "co2_month":        latest.get("month"),
            "co2_trend_1y":     trend,
            "data_source":      "NOAA GML Mauna Loa",
            "records_available": len(records),
        }

    def _fixture(self) -> Dict[str, Any]:
        return {
            "co2_ppm":          424.1,
            "co2_year":         2026,
            "co2_month":        4,
            "co2_trend_1y":     2.3,
            "data_source":      "NOAA GML (fixture/offline)",
            "records_available": 0,
        }

__all__ = ["NOAAClimateFeed"]

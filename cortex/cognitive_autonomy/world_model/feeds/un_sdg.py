"""
UN SDG Feed — M6.3
UN SDG indicators via UN Stats API (read-only).
Offline fixture: SDG progress summary per goal.
"""
from __future__ import annotations
import json
from typing import Any, Dict
from .base import FeedConnector


class UNSDGFeed(FeedConnector):
    name = "un_sdg"
    min_interval_s = 7200.0   # max 1 fetch ogni 2 ore

    def _url(self) -> str:
        # UN SDG API: list of goals with metadata
        return "https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=false"

    def _parse(self, raw: bytes) -> Dict[str, Any]:
        goals = json.loads(raw.decode("utf-8", errors="replace"))
        if not isinstance(goals, list):
            goals = []
        parsed = []
        for g in goals:
            parsed.append({
                "goal":        g.get("code", "?"),
                "title":       g.get("title", "?")[:80],
                "description": (g.get("description") or "")[:120],
            })
        return {
            "goals_count":  len(parsed),
            "goals":        parsed,
            "agenda":       "2030",
            "data_source":  "UN Statistics Division SDG API",
        }

    def _fixture(self) -> Dict[str, Any]:
        return {
            "goals_count": 17,
            "goals": [
                {"goal": "1",  "title": "No Poverty",             "description": "End poverty in all forms everywhere"},
                {"goal": "2",  "title": "Zero Hunger",            "description": "End hunger, achieve food security"},
                {"goal": "3",  "title": "Good Health",            "description": "Ensure healthy lives for all"},
                {"goal": "4",  "title": "Quality Education",      "description": "Ensure inclusive and equitable quality education"},
                {"goal": "5",  "title": "Gender Equality",        "description": "Achieve gender equality"},
                {"goal": "6",  "title": "Clean Water",            "description": "Ensure availability of water and sanitation"},
                {"goal": "7",  "title": "Affordable Energy",      "description": "Ensure access to affordable clean energy"},
                {"goal": "8",  "title": "Decent Work",            "description": "Promote sustained economic growth"},
                {"goal": "9",  "title": "Industry & Innovation",  "description": "Build resilient infrastructure"},
                {"goal": "10", "title": "Reduced Inequalities",   "description": "Reduce inequality within and among countries"},
                {"goal": "11", "title": "Sustainable Cities",     "description": "Make cities inclusive, safe, resilient"},
                {"goal": "12", "title": "Responsible Consumption","description": "Ensure sustainable consumption and production"},
                {"goal": "13", "title": "Climate Action",         "description": "Take urgent action to combat climate change"},
                {"goal": "14", "title": "Life Below Water",       "description": "Conserve oceans and marine resources"},
                {"goal": "15", "title": "Life on Land",           "description": "Protect terrestrial ecosystems"},
                {"goal": "16", "title": "Peace & Justice",        "description": "Promote peaceful and inclusive societies"},
                {"goal": "17", "title": "Partnerships",           "description": "Strengthen means of implementation"},
            ],
            "agenda": "2030",
            "data_source": "UN SDG (fixture/offline)",
        }

__all__ = ["UNSDGFeed"]

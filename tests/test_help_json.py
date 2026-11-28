"""Validate web/data/help.json structure for the UI."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELP = ROOT / "web" / "data" / "help.json"

REQUIRED_SECTIONS = [
    "quick_start",
    "how_to_run",
    "settings_explained",
    "controls",
    "ai_techniques",
    "reading_results",
    "tips",
    "troubleshooting",
    "glossary",
    "about",
]

REQUIRED_SETTINGS = [
    "map",
    "n_zombies",
    "n_humans",
    "n_healers",
    "max_rounds",
    "heal_cooldown",
    "seed",
    "vision_radius",
    "hidden_roles",
    "search_depth",
    "zombie_ai",
    "human_ai",
    "healer_ai",
    "heuristic",
    "compare_games",
    "compare_role",
    "speed",
    "vision_overlay",
    "belief_overlay",
]

REQUIRED_AGENTS = [
    "manual",
    "random",
    "rulebased",
    "bfs",
    "dfs",
    "ucs",
    "greedy",
    "astar",
    "minimax",
    "alphabeta",
    "expectimax",
    "qlearning",
    "belief",
]


class TestHelpJson(unittest.TestCase):
    """help.json must be valid and cover settings, agents and Help sections."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load help.json once."""
        cls.data = json.loads(HELP.read_text(encoding="utf-8"))

    def test_required_sections(self) -> None:
        """All ten Help sections exist with titles and bodies."""
        for key in REQUIRED_SECTIONS:
            self.assertIn(key, self.data["sections"])
            sec = self.data["sections"][key]
            self.assertIn("title", sec)
            self.assertIn("body", sec)
            self.assertTrue(sec["title"].strip())
            self.assertTrue(sec["body"].strip())

    def test_settings_structured(self) -> None:
        """Every setting has summary, default, range and tip for the Help table."""
        for key in REQUIRED_SETTINGS:
            self.assertIn(key, self.data["settings"])
            entry = self.data["settings"][key]
            self.assertIsInstance(entry, dict)
            for field in ("summary", "default", "range", "tip"):
                self.assertIn(field, entry)
                self.assertTrue(str(entry[field]).strip(), msg=f"{key}.{field}")

    def test_agents_structured(self) -> None:
        """Every agent (plus belief) has summary/strong/weak/nodes cards."""
        for key in REQUIRED_AGENTS:
            self.assertIn(key, self.data["agents"])
            card = self.data["agents"][key]
            self.assertIsInstance(card, dict)
            for field in ("summary", "strong", "weak", "nodes"):
                self.assertIn(field, card)
                self.assertTrue(str(card[field]).strip(), msg=f"{key}.{field}")

    def test_controls_and_glossary(self) -> None:
        """Controls table and glossary terms are non-empty."""
        self.assertGreaterEqual(len(self.data["controls_table"]), 8)
        for row in self.data["controls_table"]:
            self.assertIn("control", row)
            self.assertIn("action", row)
        self.assertGreaterEqual(len(self.data["glossary_terms"]), 8)
        for row in self.data["glossary_terms"]:
            self.assertIn("term", row)
            self.assertIn("def", row)

    def test_section_rich_flags(self) -> None:
        """Key sections opt into tables/cards/lists."""
        secs = self.data["sections"]
        self.assertTrue(secs["settings_explained"].get("use_settings_table"))
        self.assertTrue(secs["controls"].get("use_controls_table"))
        self.assertTrue(secs["ai_techniques"].get("use_agent_cards"))
        self.assertTrue(secs["glossary"].get("use_glossary"))
        self.assertGreaterEqual(len(secs["quick_start"]["steps"]), 5)
        self.assertGreaterEqual(len(secs["how_to_run"]["blocks"]), 3)

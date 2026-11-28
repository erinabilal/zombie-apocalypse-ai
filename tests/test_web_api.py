"""Unit tests for web_api bridge functions (no browser)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web" / "py_bridge"))

import web_api  # noqa: E402


def _load_maps() -> None:
    """Register shipped maps for the bridge."""
    maps = {}
    for path in (ROOT / "maps").glob("*.txt"):
        maps[path.stem] = path.read_text(encoding="utf-8")
    web_api.set_maps(maps)


class TestWebApi(unittest.TestCase):
    """Every bridge function returns valid JSON-serializable dicts."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load maps once for all tests."""
        _load_maps()

    def test_list_options(self) -> None:
        """list_options includes maps, agents and heuristics."""
        result = web_api.list_options()
        self.assertNotIn("error", result)
        self.assertIn("small", result["maps"])
        self.assertIn("rulebased", result["agents"])
        self.assertIn("manhattan", result["heuristics"])
        json.dumps(result)

    def test_new_game_and_step(self) -> None:
        """new_game and step return state payloads without errors."""
        created = web_api.new_game(
            {
                "map": "small",
                "seed": 0,
                "zombie_ai": "rulebased",
                "human_ai": "rulebased",
                "healer_ai": "rulebased",
                "max_rounds": 10,
            }
        )
        self.assertNotIn("error", created)
        self.assertIn("state", created)
        self.assertIn("map", created)
        self.assertIn("agents", created)
        json.dumps(created)

        stepped = web_api.step()
        self.assertNotIn("error", stepped)
        self.assertIn("event", stepped)
        self.assertIn("state", stepped)
        self.assertIn("done", stepped)
        json.dumps(stepped)

    def test_play_round(self) -> None:
        """play_round returns a list of events."""
        web_api.new_game({"map": "small", "seed": 1, "max_rounds": 5})
        result = web_api.play_round()
        self.assertNotIn("error", result)
        self.assertIsInstance(result["events"], list)
        self.assertGreaterEqual(len(result["events"]), 1)
        json.dumps(result)

    def test_submit_manual_action(self) -> None:
        """Manual action applies when provided to the current agent."""
        web_api.new_game(
            {
                "map": "small",
                "seed": 2,
                "zombie_ai": "manual",
                "human_ai": "rulebased",
                "healer_ai": "rulebased",
                "max_rounds": 5,
            }
        )
        blocked = web_api.step()
        self.assertIn("error", blocked)
        applied = web_api.submit_manual_action("STAY")
        self.assertNotIn("error", applied)
        self.assertEqual(applied["event"]["action"], "STAY")
        json.dumps(applied)

    def test_get_observation(self) -> None:
        """get_observation returns visible cells and agents."""
        created = web_api.new_game({"map": "small", "seed": 3, "vision_radius": 3})
        agent_id = created["state"]["agents"][0]["id"]
        obs = web_api.get_observation(agent_id)
        self.assertNotIn("error", obs)
        self.assertIn("visible_cells", obs)
        self.assertIn("visible_agents", obs)
        json.dumps(obs)

    def test_get_belief_map(self) -> None:
        """get_belief_map returns a cells list (possibly empty)."""
        created = web_api.new_game(
            {
                "map": "small",
                "seed": 4,
                "zombie_ai": "bfs",
                "human_ai": "rulebased",
                "healer_ai": "rulebased",
                "vision_radius": 2,
                "use_belief_tracker": True,
            }
        )
        agent_id = created["state"]["agents"][0]["id"]
        belief = web_api.get_belief_map(agent_id)
        self.assertNotIn("error", belief)
        self.assertIn("cells", belief)
        json.dumps(belief)

    def test_run_compare(self) -> None:
        """run_compare returns per-agent metric rows."""
        result = web_api.run_compare(
            {"map": "small", "seed": 0, "max_rounds": 15, "human_ai": "random", "healer_ai": "random"},
            ["random", "rulebased"],
            3,
        )
        self.assertNotIn("error", result)
        self.assertEqual(len(result["rows"]), 2)
        self.assertIn("win_rate", result["rows"][0])
        json.dumps(result)

    def test_call_dispatcher(self) -> None:
        """call() dispatches by name and rejects unknown functions."""
        result = web_api.call("list_options", [])
        self.assertNotIn("error", result)
        bad = web_api.call("nope", [])
        self.assertIn("error", bad)

    def test_load_maps_json(self) -> None:
        """load_maps_json accepts the build_web maps.json shape."""
        payload = {
            "tiny": {"text": "###\n#.#\n###", "lines": ["###", "#.#", "###"]},
        }
        web_api.load_maps_json(json.dumps(payload))
        self.assertIn("tiny", web_api.list_options()["maps"])
        _load_maps()  # restore shipped maps for other tests


if __name__ == "__main__":
    unittest.main()

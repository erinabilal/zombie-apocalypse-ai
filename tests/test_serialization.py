"""Unit tests for JSON-friendly serialization round trips."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from agents.factory import make_agent
from config import GameConfig
from game.engine import Engine, private_rng
from game.serialization import (
    config_from_dict,
    config_to_dict,
    event_from_dict,
    event_to_dict,
    result_from_dict,
    result_to_dict,
    state_from_dict,
    state_to_dict,
)

ROOT = Path(__file__).resolve().parents[1]


class TestSerialization(unittest.TestCase):
    """Round-trip config, state, events and results through dict/JSON."""

    def test_config_round_trip(self) -> None:
        """GameConfig survives dict and JSON round trips."""
        cfg = GameConfig(map_text="###\n#.#\n###", seed=3, vision_radius=4)
        data = config_to_dict(cfg)
        json.dumps(data)
        restored = config_from_dict(data)
        self.assertEqual(config_to_dict(restored), data)

    def test_state_and_event_round_trip(self) -> None:
        """State and events from a short game round-trip cleanly."""
        map_text = (ROOT / "maps" / "small.txt").read_text(encoding="utf-8")
        config = GameConfig(map_text=map_text, seed=0, max_rounds=5, zombie_ai="random", human_ai="random", healer_ai="random")
        engine = Engine(config)
        engine.reset()
        engine.controllers = {
            a.id: make_agent("random", a.id, a.role, config, private_rng(0, a.id))
            for a in engine.state.agents
        }
        engine.step()
        state_data = state_to_dict(engine.state)
        json.dumps(state_data)
        restored_state = state_from_dict(state_data)
        self.assertEqual(state_to_dict(restored_state), state_data)

        event_data = event_to_dict(engine.history[0])
        json.dumps(event_data)
        restored_event = event_from_dict(event_data)
        self.assertEqual(event_to_dict(restored_event), event_data)

        result = engine.run()
        result_data = result_to_dict(result)
        json.dumps(result_data)
        self.assertEqual(result_to_dict(result_from_dict(result_data)), result_data)


if __name__ == "__main__":
    unittest.main()

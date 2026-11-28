"""Unit tests for seeded determinism of the engine."""

from __future__ import annotations

import unittest
from pathlib import Path

from agents.factory import make_agent
from config import GameConfig
from game.engine import Engine, private_rng
from game.serialization import event_to_dict

ROOT = Path(__file__).resolve().parents[1]


def _run(seed: int, zombie_ai: str = "random", human_ai: str = "random", healer_ai: str = "random"):
    """Run one quiet game and return (result_dict, event_dicts)."""
    map_text = (ROOT / "maps" / "small.txt").read_text(encoding="utf-8")
    config = GameConfig(
        map_text=map_text,
        seed=seed,
        zombie_ai=zombie_ai,
        human_ai=human_ai,
        healer_ai=healer_ai,
        max_rounds=30,
    )
    engine = Engine(config)
    engine.reset()
    controllers = {}
    for agent in engine.state.agents:
        if agent.role.value == "zombie":
            name = zombie_ai
        elif agent.role.value == "healer":
            name = healer_ai
        else:
            name = human_ai
        controllers[agent.id] = make_agent(
            name, agent.id, agent.role, config, private_rng(seed, agent.id)
        )
    engine.controllers = controllers
    result = engine.run()
    return (
        {
            "winner": result.winner,
            "reason": result.reason,
            "rounds": result.rounds_played,
            "infections": result.infections,
            "heals": result.heals,
        },
        [event_to_dict(e) for e in engine.history],
    )


class TestDeterminism(unittest.TestCase):
    """Same seed => identical history; different seeds differ."""

    def test_same_seed_identical_history(self) -> None:
        """Two runs with the same seed produce the same event history."""
        a_result, a_events = _run(7)
        b_result, b_events = _run(7)
        self.assertEqual(a_result, b_result)
        self.assertEqual(a_events, b_events)

    def test_different_seeds_differ(self) -> None:
        """Different seeds produce different histories (with high probability)."""
        _, a_events = _run(1)
        _, b_events = _run(2)
        self.assertNotEqual(a_events, b_events)

    def test_rulebased_same_seed(self) -> None:
        """Rule-based agents are also deterministic under a fixed seed."""
        a_result, a_events = _run(11, "rulebased", "rulebased", "rulebased")
        b_result, b_events = _run(11, "rulebased", "rulebased", "rulebased")
        self.assertEqual(a_result, b_result)
        self.assertEqual(a_events, b_events)


if __name__ == "__main__":
    unittest.main()

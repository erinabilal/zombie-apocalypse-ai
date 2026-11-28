"""Unit tests for baseline agents controlling every role."""

from __future__ import annotations

import unittest
from pathlib import Path

from agents.factory import make_agent
from config import GameConfig
from game.engine import Engine, private_rng
from game.entities import Role

ROOT = Path(__file__).resolve().parents[1]
MAP = (ROOT / "maps" / "small.txt").read_text(encoding="utf-8")


class TestAgents(unittest.TestCase):
    """Random and rule-based agents play every role without errors."""

    def _play(self, name: str, rounds: int = 50, **config_overrides) -> None:
        """Run a game where every role uses the same agent name."""
        kwargs = dict(
            map_text=MAP,
            seed=0,
            max_rounds=rounds,
            zombie_ai=name,
            human_ai=name,
            healer_ai=name,
        )
        kwargs.update(config_overrides)
        config = GameConfig(**kwargs)
        engine = Engine(config)
        engine.reset()
        engine.controllers = {
            a.id: make_agent(name, a.id, a.role, config, private_rng(config.seed, a.id))
            for a in engine.state.agents
        }
        result = engine.run()
        self.assertIn(result.winner, ("zombies", "humans"))
        self.assertGreater(len(engine.history), 0)

    def test_random_every_role_50_rounds(self) -> None:
        """RandomAgent can control every role for up to 50 rounds."""
        self._play("random", 50)

    def test_rulebased_every_role_50_rounds(self) -> None:
        """RuleBasedAgent can control every role for up to 50 rounds."""
        self._play("rulebased", 50)

    def test_search_agents_every_role_50_rounds(self) -> None:
        """Each search algorithm can control every role for up to 50 rounds."""
        for name in ("bfs", "dfs", "ucs", "greedy", "astar"):
            with self.subTest(name=name):
                self._play(name, 50)

    def test_adversarial_agents_every_role_50_rounds(self) -> None:
        """Minimax/alpha-beta/expectimax can control every role for up to 50 rounds."""
        for name in ("minimax", "alphabeta", "expectimax"):
            with self.subTest(name=name):
                self._play(
                    name,
                    50,
                    search_depth=1,
                    move_time_limit=2.0,
                    node_budget=2000,
                )

    def test_qlearning_every_role_50_rounds(self) -> None:
        """Q-learning agent (fallback without table) controls every role for 50 rounds."""
        self._play("qlearning", 50)

    def test_factory_rejects_unknown(self) -> None:
        """Unknown agent names raise ValueError."""
        config = GameConfig(map_text=MAP)
        with self.assertRaises(ValueError):
            make_agent("not-an-agent", 0, Role.ZOMBIE, config, private_rng(0, 0))


if __name__ == "__main__":
    unittest.main()

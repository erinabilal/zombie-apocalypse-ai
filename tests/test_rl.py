"""Unit tests for RL rewards, Q-learning updates and a short training run."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config import GameConfig
from game.entities import Action, Role
from rl.environment import ZombieEnv, compute_reward, encode_state
from rl.q_learning import QTable, epsilon_for_episode, train_episodes
from rl.train import train

ROOT = Path(__file__).resolve().parents[1]
MAP = (ROOT / "maps" / "small.txt").read_text(encoding="utf-8")


class TestRewards(unittest.TestCase):
    """Reward table matches GameConfig constants."""

    def test_reward_table(self) -> None:
        """Known reward combinations."""
        cfg = GameConfig(map_text=MAP)
        self.assertAlmostEqual(
            compute_reward(
                cfg, Role.HUMAN, infections=0, heals=0, infected_self=False, survived_round=True, winner=None
            ),
            cfg.reward_human_survive_round,
        )
        self.assertAlmostEqual(
            compute_reward(
                cfg, Role.ZOMBIE, infections=2, heals=0, infected_self=False, survived_round=False, winner="zombies"
            ),
            2 * cfg.reward_zombie_infection + cfg.reward_zombie_step + cfg.reward_zombie_win,
        )
        self.assertAlmostEqual(
            compute_reward(
                cfg, Role.HEALER, infections=0, heals=1, infected_self=True, survived_round=False, winner=None
            ),
            cfg.reward_healer_heal + cfg.reward_healer_infected,
        )


class TestQLearning(unittest.TestCase):
    """Tabular updates, epsilon schedule, env smoke, short train."""

    def test_epsilon_decay(self) -> None:
        """Epsilon starts near 1 and ends at 0.05 after 60% of episodes."""
        self.assertAlmostEqual(epsilon_for_episode(0, 100), 1.0)
        self.assertAlmostEqual(epsilon_for_episode(60, 100), 0.05)
        self.assertAlmostEqual(epsilon_for_episode(99, 100), 0.05)

    def test_q_update_and_json(self) -> None:
        """One TD update changes Q and round-trips through JSON."""
        table = QTable()
        state = (0, 0, None, None, 0, 0, 0, 0, 0, 2, "human")
        nxt = (1, 0, None, None, 0, 0, 0, 0, 0, 2, "human")
        table.update(state, Action.RIGHT, 1.0, nxt, [Action.STAY], alpha=0.1, gamma=0.95, done=False)
        self.assertGreater(table.get(state, Action.RIGHT), 0.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.json"
            table.save(path)
            loaded = QTable.load(path)
            self.assertAlmostEqual(loaded.get(state, Action.RIGHT), table.get(state, Action.RIGHT))

    def test_env_reset_step(self) -> None:
        """ZombieEnv reset/step returns finite rewards and a terminal flag."""
        cfg = GameConfig(
            map_text=MAP,
            seed=0,
            max_rounds=20,
            n_zombies=1,
            n_humans=2,
            n_healers=0,
            move_time_limit=5.0,
        )
        env = ZombieEnv(cfg, learner_role=Role.HUMAN, opponent_ai="random")
        state = env.reset(seed=0)
        self.assertIsInstance(state, tuple)
        legal = env.legal_actions()
        self.assertTrue(legal)
        nxt, reward, done, info = env.step(legal[0])
        self.assertIsInstance(nxt, tuple)
        self.assertIsInstance(reward, float)
        self.assertIn("winner", info)
        self.assertIsInstance(done, bool)

    def test_short_training_run(self) -> None:
        """A tiny training run writes a non-empty Q-table."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "human_small.json"
            curve = Path(tmp) / "curve.csv"
            table_path, curve_path = train(
                role="human",
                map_path=str(ROOT / "maps" / "small.txt"),
                episodes=8,
                seed=0,
                opponent="random",
                n_humans=2,
                n_healers=0,
                max_rounds=15,
                out=out,
                curve_path=curve,
            )
            self.assertTrue(table_path.is_file())
            self.assertTrue(curve_path.is_file())
            table = QTable.load(table_path)
            self.assertGreater(len(table.q), 0)

    def test_train_episodes_direct(self) -> None:
        """train_episodes returns one row per episode."""
        cfg = GameConfig(
            map_text=MAP,
            seed=1,
            max_rounds=10,
            n_humans=2,
            n_healers=0,
            move_time_limit=5.0,
        )
        env = ZombieEnv(cfg, learner_role=Role.ZOMBIE, opponent_ai="random")
        table = QTable()
        curve = train_episodes(env, table, 3, seed=1)
        self.assertEqual(len(curve), 3)


if __name__ == "__main__":
    unittest.main()

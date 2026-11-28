"""Unit tests for evaluation.metrics (Wilson interval, aggregates, CSV)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.compare_mode import compare_agents, run_one_game
from evaluation.experiments import EXPERIMENTS, base_config, iter_settings, list_experiments
from evaluation.metrics import (
    aggregate_by,
    mean_std,
    read_records_csv,
    wilson_interval,
    write_records_csv,
)


class TestWilson(unittest.TestCase):
    """Wilson 95% interval on known inputs."""

    def test_perfect_and_zero(self) -> None:
        """All wins / no wins stay inside [0, 1] with a sensible Wilson width."""
        lo, hi = wilson_interval(10, 10)
        self.assertGreater(lo, 0.7)
        self.assertLessEqual(hi, 1.0)
        self.assertLess(lo, 1.0)
        lo0, hi0 = wilson_interval(0, 10)
        self.assertGreaterEqual(lo0, 0.0)
        self.assertLess(hi0, 0.3)
        mid_lo, mid_hi = wilson_interval(5, 10)
        self.assertLessEqual(mid_lo, 0.5)
        self.assertGreaterEqual(mid_hi, 0.5)

    def test_empty(self) -> None:
        """n=0 returns (0, 0)."""
        self.assertEqual(wilson_interval(0, 0), (0.0, 0.0))

    def test_mean_std(self) -> None:
        """Mean/std for a tiny series."""
        m, s = mean_std([1.0, 3.0])
        self.assertAlmostEqual(m, 2.0)
        self.assertAlmostEqual(s, 2.0**0.5)


class TestExperiments(unittest.TestCase):
    """Experiment registry and a tiny smoke run."""

    def test_seven_registered(self) -> None:
        """All seven experiment names exist."""
        names = list_experiments()
        self.assertEqual(len(names), 7)
        self.assertIn("healer_ablation", names)
        self.assertFalse(EXPERIMENTS["learned_vs_baselines"].requires_qlearning)

    def test_settings_nonempty(self) -> None:
        """Every runnable experiment yields at least one setting."""
        for name in list_experiments():
            if EXPERIMENTS[name].requires_qlearning:
                continue
            cells = list(iter_settings(name))
            self.assertGreater(len(cells), 0, msg=name)

    def test_run_one_and_csv(self) -> None:
        """One game produces a record that round-trips through CSV."""
        cfg, map_name = base_config(
            "small",
            zombie_ai="random",
            human_ai="random",
            healer_ai="random",
            max_rounds=20,
            seed=1,
        )
        rec = run_one_game(cfg, map_name=map_name, label="smoke")
        self.assertIn(rec.winner, {"zombies", "humans"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "smoke.csv"
            write_records_csv(path, [rec])
            rows = read_records_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["winner"], rec.winner)

    def test_compare_agents_small(self) -> None:
        """Compare two cheap agents for 2 games."""
        cfg, map_name = base_config(
            "small",
            human_ai="random",
            healer_ai="random",
            max_rounds=15,
            seed=0,
        )
        rows = compare_agents(cfg, ["random", "rulebased"], 2, role="zombie", map_name=map_name)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["games"], 2)
        self.assertIn("win_rate_lo", rows[0])
        agg = aggregate_by(
            [
                {"winner": "zombies", "rounds_played": 5, "avg_nodes_expanded": 1, "avg_time_per_move": 0},
                {"winner": "humans", "rounds_played": 7, "avg_nodes_expanded": 3, "avg_time_per_move": 0},
            ],
            (),
            win_side="zombies",
        )
        self.assertEqual(agg[0]["wins"], 1)


if __name__ == "__main__":
    unittest.main()

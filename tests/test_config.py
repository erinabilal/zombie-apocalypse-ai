"""Unit tests for GameConfig defaults and validation."""

import dataclasses
import unittest

from config import AGENT_NAMES, DEFAULTS, GameConfig

MAP = "#####\n#...#\n#####"


class TestGameConfig(unittest.TestCase):
    """GameConfig defaults, immutability and validation."""

    def test_defaults(self) -> None:
        """Default values match the project brief."""
        cfg = GameConfig(map_text=MAP)
        self.assertEqual((cfg.n_zombies, cfg.n_humans, cfg.n_healers), (1, 4, 1))
        self.assertEqual(cfg.max_rounds, 60)
        self.assertEqual(cfg.heal_cooldown, 3)
        self.assertEqual(cfg.seed, 0)
        self.assertIsNone(cfg.vision_radius)
        self.assertFalse(cfg.hidden_roles)
        self.assertEqual(cfg.identify_radius, 2)
        self.assertEqual(cfg.min_spawn_distance, 6)
        self.assertEqual((cfg.zombie_ai, cfg.human_ai, cfg.healer_ai), ("rulebased",) * 3)
        self.assertEqual(cfg.search_depth, 2)
        self.assertEqual(cfg.move_time_limit, 1.0)
        self.assertEqual(cfg.reward_zombie_win, 20.0)

    def test_defaults_dict_matches_fields(self) -> None:
        """DEFAULTS covers every field except map_text."""
        names = {f.name for f in dataclasses.fields(GameConfig)}
        self.assertEqual(set(DEFAULTS), names - {"map_text"})

    def test_frozen(self) -> None:
        """Assigning to a field raises FrozenInstanceError."""
        cfg = GameConfig(map_text=MAP)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cfg.seed = 5  # type: ignore[misc]

    def test_replace_revalidates(self) -> None:
        """dataclasses.replace runs validation again."""
        cfg = GameConfig(map_text=MAP)
        with self.assertRaises(ValueError):
            dataclasses.replace(cfg, max_rounds=0)

    def test_all_agent_names_accepted(self) -> None:
        """Every agent name is valid for every role."""
        for name in AGENT_NAMES:
            GameConfig(map_text=MAP, zombie_ai=name, human_ai=name, healer_ai=name)

    def test_valid_edge_values(self) -> None:
        """Boundary values that should be accepted."""
        GameConfig(map_text=MAP, n_humans=0, n_healers=1)
        GameConfig(map_text=MAP, n_healers=0)
        GameConfig(map_text=MAP, vision_radius=1, search_depth=6, heal_cooldown=1)
        GameConfig(map_text=MAP, seed=-3, node_budget=100)

    def test_invalid_values(self) -> None:
        """Each invalid value raises ValueError."""
        bad = [
            {"map_text": ""},
            {"map_text": "   "},
            {"n_zombies": 0},
            {"n_humans": 0, "n_healers": 0},
            {"n_humans": -1},
            {"n_healers": -1},
            {"max_rounds": 0},
            {"heal_cooldown": 0},
            {"vision_radius": 0},
            {"identify_radius": -1},
            {"min_spawn_distance": -1},
            {"zombie_ai": "nope"},
            {"human_ai": "AStar"},
            {"healer_ai": ""},
            {"search_depth": 0},
            {"search_depth": 7},
            {"move_time_limit": 0},
            {"move_time_limit": -1.0},
            {"node_budget": 0},
            {"heuristic": "chebyshev"},
            {"relevance_radius": 0},
            {"opponent_model": "greedy"},
            {"n_zombies": 1.5},
            {"n_zombies": True},
            {"hidden_roles": 1},
            {"use_belief_tracker": "yes"},
            {"reward_human_win": "10"},
        ]
        for overrides in bad:
            kwargs = {"map_text": MAP, **overrides}
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                GameConfig(**kwargs)


if __name__ == "__main__":
    unittest.main()

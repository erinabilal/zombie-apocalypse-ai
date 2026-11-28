"""Unit tests for Grid parsing, neighbors, costs and connectivity."""

from __future__ import annotations

import unittest
from pathlib import Path

from game.entities import Action
from game.grid import Grid

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "maps"


class TestGrid(unittest.TestCase):
    """Grid.from_lines validation and helpers."""

    def test_shipped_maps_load_and_connected(self) -> None:
        """All three shipped maps load and have no unreachable floor cells."""
        for name in ("small.txt", "medium.txt", "large.txt"):
            with self.subTest(map=name):
                grid = Grid.from_file(str(MAPS / name))
                self.assertIsNone(grid.first_unreachable())
                self.assertGreater(grid.width, 0)
                self.assertGreater(len(grid.floor_cells()), 0)

    def test_shipped_map_sizes(self) -> None:
        """Shipped maps match the planned approximate sizes."""
        small = Grid.from_file(str(MAPS / "small.txt"))
        medium = Grid.from_file(str(MAPS / "medium.txt"))
        large = Grid.from_file(str(MAPS / "large.txt"))
        self.assertEqual((small.width, small.height), (10, 10))
        self.assertEqual((medium.width, medium.height), (20, 15))
        self.assertEqual((large.width, large.height), (30, 20))

    def test_ragged_map_rejected(self) -> None:
        """Rows of different lengths raise ValueError."""
        with self.assertRaises(ValueError):
            Grid.from_lines(["###", "##", "###"])

    def test_disconnected_map_rejected(self) -> None:
        """A floor island reports the first unreachable cell."""
        lines = [
            "#####",
            "#.#.#",
            "#####",
        ]
        with self.assertRaises(ValueError) as ctx:
            Grid.from_lines(lines)
        self.assertIn("unreachable", str(ctx.exception))
        self.assertIn("(3, 1)", str(ctx.exception))

    def test_illegal_character_rejected(self) -> None:
        """Unknown characters are rejected."""
        with self.assertRaises(ValueError):
            Grid.from_lines(["###", "#X#", "###"])

    def test_weighted_costs(self) -> None:
        """Digits set terrain costs; '.' is cost 1."""
        grid = Grid.from_lines(["####", "#.2#", "#3.#", "####"])
        self.assertEqual(grid.cost(1, 1), 1)
        self.assertEqual(grid.cost(2, 1), 2)
        self.assertEqual(grid.cost(1, 2), 3)

    def test_spawn_markers(self) -> None:
        """Z/H/D markers are recorded and treated as cost-1 floor."""
        grid = Grid.from_lines(["#####", "#ZHD#", "#####"])
        self.assertEqual(grid.spawn_markers[(1, 1)], "Z")
        self.assertEqual(grid.spawn_markers[(2, 1)], "H")
        self.assertEqual(grid.spawn_markers[(3, 1)], "D")
        self.assertEqual(grid.cost(1, 1), 1)

    def test_neighbor_order(self) -> None:
        """neighbors and neighbor_actions use UP, DOWN, LEFT, RIGHT order."""
        grid = Grid.from_lines(
            [
                "#####",
                "#...#",
                "#...#",
                "#...#",
                "#####",
            ]
        )
        self.assertEqual(grid.neighbors(2, 2), [(2, 1), (2, 3), (1, 2), (3, 2)])
        self.assertEqual(
            grid.neighbor_actions(2, 2),
            [Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT],
        )

    def test_bfs_distance(self) -> None:
        """bfs_distance returns step count or None."""
        grid = Grid.from_lines(["#####", "#...#", "#####"])
        self.assertEqual(grid.bfs_distance((1, 1), (3, 1)), 2)
        self.assertEqual(grid.bfs_distance((1, 1), (1, 1)), 0)

    def test_from_lines_string(self) -> None:
        """from_lines accepts a single multiline string."""
        grid = Grid.from_lines("###\n#.#\n###")
        self.assertEqual(grid.width, 3)
        self.assertEqual(grid.height, 3)

    def test_empty_map_rejected(self) -> None:
        """Empty input raises ValueError."""
        with self.assertRaises(ValueError):
            Grid.from_lines([])


if __name__ == "__main__":
    unittest.main()

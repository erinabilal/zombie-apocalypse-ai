"""Unit tests for pathfinding search and heuristics."""

from __future__ import annotations

import unittest
from pathlib import Path

from game.entities import Action
from game.grid import Grid
from search.heuristics import MazeDistance, euclidean, manhattan
from search.informed import astar, greedy
from search.problem import PathProblem
from search.uninformed import bfs, dfs, ucs

ROOT = Path(__file__).resolve().parents[1]


def _goal_set(goals: set[tuple[int, int]]):
    """Build a goal_test for a fixed set of cells."""
    return lambda c: c in goals


class TestSearch(unittest.TestCase):
    """BFS/DFS/UCS/Greedy/A* correctness on handcrafted maps."""

    def test_bfs_optimal_in_steps(self) -> None:
        """BFS finds a shortest path in number of steps."""
        grid = Grid.from_lines(
            [
                "#####",
                "#...#",
                "#.#.#",
                "#...#",
                "#####",
            ]
        )
        problem = PathProblem(grid, (1, 1), _goal_set({(3, 3)}))
        result = bfs(problem)
        self.assertTrue(result.found)
        self.assertEqual(len(result.actions), 4)  # e.g. right,right,down,down

    def test_ucs_optimal_in_cost_where_bfs_is_not(self) -> None:
        """On a weighted map, UCS minimizes cost while BFS minimizes steps."""
        # Two paths from (1,1) to (3,1):
        # short expensive: right into 9, right into goal cell cost — wait goal is position.
        # Path A: (1,1)->(2,1 cost 9)->(3,1 cost 1) = cost 10, 2 steps
        # Path B: (1,1)->(1,2 cost 1)->(2,2 cost 1)->(3,2 cost 1)->(3,1 cost 1) = cost 4, 4 steps
        grid = Grid.from_lines(
            [
                "#####",
                "#.9.#",
                "#...#",
                "#####",
            ]
        )
        problem = PathProblem(grid, (1, 1), _goal_set({(3, 1)}), blocked=frozenset())
        bfs_result = bfs(problem)
        ucs_result = ucs(problem)
        self.assertTrue(bfs_result.found and ucs_result.found)
        self.assertEqual(len(bfs_result.actions), 2)
        self.assertEqual(bfs_result.cost, 10.0)
        self.assertEqual(ucs_result.cost, 4.0)
        self.assertGreater(len(ucs_result.actions), len(bfs_result.actions))

    def test_astar_equals_ucs_cost(self) -> None:
        """A* with manhattan returns the same optimal cost as UCS."""
        grid = Grid.from_lines(
            [
                "######",
                "#....#",
                "#.##.#",
                "#....#",
                "######",
            ]
        )
        goal = (4, 3)
        problem = PathProblem(grid, (1, 1), _goal_set({goal}))
        h = lambda c: manhattan(c, goal)
        self.assertEqual(astar(problem, h).cost, ucs(problem).cost)

    def test_greedy_can_be_suboptimal(self) -> None:
        """Greedy may take more steps than BFS on a deceptive layout."""
        # Greedy with manhattan toward (4,1) prefers moving right into a dead-end spur.
        grid = Grid.from_lines(
            [
                "#######",
                "#.....#",
                "#.###.#",
                "#.#...#",
                "#.#.###",
                "#.....#",
                "#######",
            ]
        )
        start = (1, 5)
        goal = (5, 1)
        problem = PathProblem(grid, start, _goal_set({goal}))
        h = lambda c: manhattan(c, goal)
        g_result = greedy(problem, h)
        b_result = bfs(problem)
        self.assertTrue(g_result.found and b_result.found)
        # Greedy is allowed to be longer; if it luckily matches, still a valid path.
        self.assertGreaterEqual(len(g_result.actions), len(b_result.actions))

    def test_no_path(self) -> None:
        """Search reports failure when every corridor to the goal is blocked."""
        grid = Grid.from_lines(
            [
                "#####",
                "#...#",
                "#####",
            ]
        )
        # Seal the only path with blocked cells.
        problem = PathProblem(
            grid, (1, 1), _goal_set({(3, 1)}), blocked=frozenset({(2, 1)})
        )
        for fn in (bfs, dfs, ucs):
            with self.subTest(fn=fn.__name__):
                result = fn(problem)
                self.assertFalse(result.found)

    def test_start_equals_goal(self) -> None:
        """When start is already a goal, the path is empty and cost is 0."""
        grid = Grid.from_lines(["###", "#.#", "###"])
        problem = PathProblem(grid, (1, 1), _goal_set({(1, 1)}))
        for fn in (bfs, dfs, ucs):
            with self.subTest(fn=fn.__name__):
                result = fn(problem)
                self.assertTrue(result.found)
                self.assertEqual(result.actions, ())
                self.assertEqual(result.cost, 0.0)

    def test_dfs_finds_some_path(self) -> None:
        """DFS finds a path (not necessarily optimal) within the depth limit."""
        grid = Grid.from_lines(
            [
                "#####",
                "#...#",
                "#.#.#",
                "#...#",
                "#####",
            ]
        )
        problem = PathProblem(grid, (1, 1), _goal_set({(3, 3)}))
        result = dfs(problem)
        self.assertTrue(result.found)
        self.assertGreaterEqual(len(result.actions), 4)

    def test_blocked_cells_respected(self) -> None:
        """Blocked cells cannot be traversed."""
        grid = Grid.from_lines(["#####", "#...#", "#####"])
        problem = PathProblem(
            grid, (1, 1), _goal_set({(3, 1)}), blocked=frozenset({(2, 1)})
        )
        self.assertFalse(bfs(problem).found)

    def test_successor_order_deterministic(self) -> None:
        """Equal-length BFS ties break via UP,DOWN,LEFT,RIGHT generation order."""
        grid = Grid.from_lines(
            [
                "#####",
                "#...#",
                "#...#",
                "#...#",
                "#####",
            ]
        )
        problem = PathProblem(grid, (2, 2), _goal_set({(2, 1), (2, 3), (1, 2), (3, 2)}))
        result = bfs(problem)
        self.assertTrue(result.found)
        # Closest goals are adjacent; first expanded goal neighbor is UP.
        self.assertEqual(result.actions[0], Action.UP)


class TestHeuristics(unittest.TestCase):
    """Admissibility and consistency checks on small.txt."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load small.txt once for pairwise checks."""
        cls.grid = Grid.from_file(str(ROOT / "maps" / "small.txt"))
        cls.floors = cls.grid.floor_cells()
        cls.maze = MazeDistance(cls.grid)

    def test_manhattan_admissible_and_consistent(self) -> None:
        """Manhattan never overestimates true cost and satisfies consistency."""
        # Sample pairs for speed; include a full local neighborhood check.
        samples = self.floors[::3]
        for goal in samples[:8]:
            for a in samples:
                true_steps = self.grid.bfs_distance(a, goal)
                if true_steps is None:
                    continue
                # Min step cost is 1 => true cost >= steps >= manhattan.
                self.assertLessEqual(manhattan(a, goal), true_steps)
                self.assertLessEqual(manhattan(a, goal), float(true_steps))
                for n in self.grid.neighbors(*a):
                    # Consistency: h(a) <= c(a,n) + h(n) with c >= 1.
                    self.assertLessEqual(
                        manhattan(a, goal),
                        self.grid.cost(*n) + manhattan(n, goal),
                    )

    def test_euclidean_admissible(self) -> None:
        """Euclidean never exceeds true step count (min cost 1)."""
        for goal in self.floors[::5][:6]:
            for a in self.floors[::5]:
                true_steps = self.grid.bfs_distance(a, goal)
                if true_steps is None:
                    continue
                self.assertLessEqual(euclidean(a, goal), float(true_steps) + 1e-9)

    def test_maze_distance_exact_steps(self) -> None:
        """Cached maze_distance matches BFS step distance."""
        for a in self.floors[::7][:5]:
            for b in self.floors[::11][:5]:
                expected = self.grid.bfs_distance(a, b)
                if expected is None:
                    continue
                self.assertEqual(self.maze(a, b), float(expected))


if __name__ == "__main__":
    unittest.main()

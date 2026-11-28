"""Heuristics: manhattan, euclidean and cached BFS maze_distance."""

from __future__ import annotations

import math
from collections import deque

from game.grid import Grid

Cell = tuple[int, int]


def manhattan(a: Cell, b: Cell) -> float:
    """Manhattan distance (admissible and consistent when min step cost is 1)."""
    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def euclidean(a: Cell, b: Cell) -> float:
    """Euclidean distance (admissible but weaker / less informed)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


class MazeDistance:
    """Cached all-pairs (or all-from-source) BFS step distances on a grid."""

    def __init__(self, grid: Grid) -> None:
        """Create an empty cache for the given grid."""
        self.grid = grid
        self._from_source: dict[Cell, dict[Cell, int]] = {}

    def __call__(self, a: Cell, b: Cell) -> float:
        """Return BFS step distance from a to b, or a large finite value if unreachable."""
        if a == b:
            return 0.0
        table = self._from_source.get(a)
        if table is None:
            table = self._bfs_all(a)
            self._from_source[a] = table
        dist = table.get(b)
        return float(dist) if dist is not None else float(10**9)

    def _bfs_all(self, start: Cell) -> dict[Cell, int]:
        """Compute BFS distances from start to every reachable floor cell."""
        if not self.grid.is_floor(*start):
            return {}
        dist: dict[Cell, int] = {start: 0}
        queue: deque[Cell] = deque([start])
        while queue:
            cell = queue.popleft()
            d = dist[cell]
            for nxt in self.grid.neighbors(*cell):
                if nxt not in dist:
                    dist[nxt] = d + 1
                    queue.append(nxt)
        return dist


def heuristic_to_nearest(
    cell: Cell,
    goals: list[Cell],
    kind: str,
    maze: MazeDistance | None = None,
) -> float:
    """Return h(cell) as the minimum heuristic distance to any goal cell."""
    if not goals:
        return 0.0
    if kind == "manhattan":
        return min(manhattan(cell, g) for g in goals)
    if kind == "euclidean":
        return min(euclidean(cell, g) for g in goals)
    if kind == "maze":
        if maze is None:
            raise ValueError("maze heuristic requires a MazeDistance instance")
        return min(maze(cell, g) for g in goals)
    raise ValueError(f"unknown heuristic {kind!r}")

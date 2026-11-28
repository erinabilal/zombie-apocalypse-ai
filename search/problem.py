"""PathProblem definition and the SearchResult record."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from game.entities import ACTION_DELTAS, MOVE_ACTIONS, Action
from game.grid import Grid

Cell = tuple[int, int]
GoalTest = Callable[[Cell], bool]


@dataclass(frozen=True)
class SearchResult:
    """Outcome of a pathfinding search."""

    found: bool
    path: tuple[Cell, ...]
    actions: tuple[Action, ...]
    cost: float
    nodes_expanded: int
    nodes_generated: int
    max_frontier_size: int
    time_seconds: float

    @staticmethod
    def failure(
        nodes_expanded: int = 0,
        nodes_generated: int = 0,
        max_frontier_size: int = 0,
        time_seconds: float = 0.0,
    ) -> SearchResult:
        """Return an empty unsuccessful result with the given counters."""
        return SearchResult(
            found=False,
            path=(),
            actions=(),
            cost=0.0,
            nodes_expanded=nodes_expanded,
            nodes_generated=nodes_generated,
            max_frontier_size=max_frontier_size,
            time_seconds=time_seconds,
        )


@dataclass
class PathProblem:
    """Grid pathfinding: state is a cell; step cost is terrain cost of the entered cell."""

    grid: Grid
    start: Cell
    goal_test: GoalTest
    blocked: frozenset[Cell] = field(default_factory=frozenset)

    def is_goal(self, cell: Cell) -> bool:
        """Return True if cell satisfies the goal test."""
        return self.goal_test(cell)

    def successors(self, cell: Cell) -> list[tuple[Action, Cell, int]]:
        """Return (action, next_cell, step_cost) in order UP, DOWN, LEFT, RIGHT."""
        result: list[tuple[Action, Cell, int]] = []
        x, y = cell
        for action in MOVE_ACTIONS:
            dx, dy = ACTION_DELTAS[action]
            nx, ny = x + dx, y + dy
            nxt = (nx, ny)
            if not self.grid.is_floor(nx, ny) or nxt in self.blocked:
                continue
            result.append((action, nxt, self.grid.cost(nx, ny)))
        return result

    def depth_limit(self) -> int:
        """DFS depth limit: width * height."""
        return self.grid.width * self.grid.height


def reconstruct_path(
    came_from: dict[Cell, tuple[Cell | None, Action | None]],
    start: Cell,
    goal: Cell,
) -> tuple[tuple[Cell, ...], tuple[Action, ...]]:
    """Rebuild path and actions from a came_from map."""
    cells: list[Cell] = [goal]
    actions: list[Action] = []
    current = goal
    while current != start:
        prev, action = came_from[current]
        assert prev is not None and action is not None
        actions.append(action)
        cells.append(prev)
        current = prev
    cells.reverse()
    actions.reverse()
    return tuple(cells), tuple(actions)

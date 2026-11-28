"""Grid parsing (from_lines/from_file), walls, terrain costs, neighbors and connectivity check."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from game.entities import ACTION_DELTAS, MOVE_ACTIONS, Action

FLOOR_CHARS = frozenset(".123456789ZHD")
ALLOWED_CHARS = FLOOR_CHARS | frozenset("#")


@dataclass(frozen=True)
class Grid:
    """Rectangular maze: walls, floor costs and spawn markers."""

    width: int
    height: int
    walls: frozenset[tuple[int, int]]
    costs: dict[tuple[int, int], int]
    spawn_markers: dict[tuple[int, int], str]

    @classmethod
    def from_lines(cls, lines: Iterable[str] | str) -> Grid:
        """Parse a rectangular map from text lines and validate connectivity."""
        if isinstance(lines, str):
            raw = lines.splitlines()
        else:
            raw = list(lines)
        rows = [line.rstrip("\n\r") for line in raw if line is not None]
        if not rows:
            raise ValueError("map is empty")
        width = len(rows[0])
        if width == 0:
            raise ValueError("map has empty first row")
        for y, row in enumerate(rows):
            if len(row) != width:
                raise ValueError(f"ragged map: row {y} has length {len(row)}, expected {width}")
            for x, ch in enumerate(row):
                if ch not in ALLOWED_CHARS:
                    raise ValueError(f"illegal character {ch!r} at ({x}, {y})")
        height = len(rows)
        walls: set[tuple[int, int]] = set()
        costs: dict[tuple[int, int], int] = {}
        spawn_markers: dict[tuple[int, int], str] = {}
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    walls.add((x, y))
                    continue
                if ch == ".":
                    costs[(x, y)] = 1
                elif ch.isdigit():
                    costs[(x, y)] = int(ch)
                elif ch in "ZHD":
                    costs[(x, y)] = 1
                    spawn_markers[(x, y)] = ch
                else:
                    raise ValueError(f"illegal character {ch!r} at ({x}, {y})")
        grid = cls(
            width=width,
            height=height,
            walls=frozenset(walls),
            costs=costs,
            spawn_markers=spawn_markers,
        )
        unreachable = grid.first_unreachable()
        if unreachable is not None:
            raise ValueError(f"disconnected map: first unreachable floor cell {unreachable}")
        return grid

    @classmethod
    def from_file(cls, path: str) -> Grid:
        """Load a map from a text file path (desktop/CLI only; browser uses from_lines)."""
        with open(path, encoding="utf-8") as handle:
            return cls.from_lines(handle.read())

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if (x, y) lies inside the rectangle."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        """Return True if the cell is a wall or out of bounds."""
        return not self.in_bounds(x, y) or (x, y) in self.walls

    def is_floor(self, x: int, y: int) -> bool:
        """Return True if the cell is a passable floor tile."""
        return self.in_bounds(x, y) and (x, y) not in self.walls

    def cost(self, x: int, y: int) -> int:
        """Return the terrain movement cost of a floor cell (>= 1)."""
        if not self.is_floor(x, y):
            raise ValueError(f"no terrain cost for non-floor cell ({x}, {y})")
        return self.costs[(x, y)]

    def floor_cells(self) -> list[tuple[int, int]]:
        """Return all floor cells in row-major order (top-left scan)."""
        return [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in self.walls
        ]

    def neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """Return passable orthogonal neighbors in order UP, DOWN, LEFT, RIGHT."""
        result: list[tuple[int, int]] = []
        for action in MOVE_ACTIONS:
            dx, dy = ACTION_DELTAS[action]
            nx, ny = x + dx, y + dy
            if self.is_floor(nx, ny):
                result.append((nx, ny))
        return result

    def neighbor_actions(self, x: int, y: int) -> list[Action]:
        """Return move actions that lead to passable neighbors (UP, DOWN, LEFT, RIGHT)."""
        result: list[Action] = []
        for action in MOVE_ACTIONS:
            dx, dy = ACTION_DELTAS[action]
            nx, ny = x + dx, y + dy
            if self.is_floor(nx, ny):
                result.append(action)
        return result

    def first_unreachable(self) -> tuple[int, int] | None:
        """Return the first floor cell (row-major) not reachable from the first floor cell."""
        floors = self.floor_cells()
        if not floors:
            return None
        start = floors[0]
        seen: set[tuple[int, int]] = {start}
        queue: deque[tuple[int, int]] = deque([start])
        while queue:
            cx, cy = queue.popleft()
            for nx, ny in self.neighbors(cx, cy):
                if (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        for cell in floors:
            if cell not in seen:
                return cell
        return None

    def bfs_distance(self, start: tuple[int, int], goal: tuple[int, int]) -> int | None:
        """Return the shortest path length in steps, or None if unreachable."""
        if start == goal:
            return 0
        if not self.is_floor(*start) or not self.is_floor(*goal):
            return None
        seen: set[tuple[int, int]] = {start}
        queue: deque[tuple[tuple[int, int], int]] = deque([(start, 0)])
        while queue:
            (cx, cy), dist = queue.popleft()
            for nx, ny in self.neighbors(cx, cy):
                if (nx, ny) in seen:
                    continue
                if (nx, ny) == goal:
                    return dist + 1
                seen.add((nx, ny))
                queue.append(((nx, ny), dist + 1))
        return None

    def to_lines(self) -> list[str]:
        """Render the grid as map text lines (markers overwrite plain floor)."""
        lines: list[str] = []
        for y in range(self.height):
            chars: list[str] = []
            for x in range(self.width):
                if (x, y) in self.walls:
                    chars.append("#")
                elif (x, y) in self.spawn_markers:
                    chars.append(self.spawn_markers[(x, y)])
                else:
                    cost = self.costs[(x, y)]
                    chars.append("." if cost == 1 else str(cost))
            lines.append("".join(chars))
        return lines

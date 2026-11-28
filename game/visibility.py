"""Line of sight, observe() and hidden-roles filtering."""

from __future__ import annotations

from dataclasses import dataclass

from game.entities import Role
from game.grid import Grid
from game.state import GameState


@dataclass(frozen=True)
class VisibleAgent:
    """One other agent as seen by the observer (role may be hidden)."""

    id: int
    x: int
    y: int
    role: Role | None


@dataclass(frozen=True)
class Observation:
    """What one agent can see at decision time."""

    self_id: int
    self_x: int
    self_y: int
    self_role: Role
    self_cooldown: int
    round_number: int
    rounds_left: int
    visible_cells: frozenset[tuple[int, int]]
    visible_agents: tuple[VisibleAgent, ...]
    grid: Grid
    legal_actions: tuple  # filled by engine/observe helper; Action values


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Return all cells on the Bresenham line from (x0,y0) to (x1,y1), including endpoints."""
    points: list[tuple[int, int]] = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points


def has_line_of_sight(grid: Grid, x0: int, y0: int, x1: int, y1: int) -> bool:
    """Return True if no wall lies on the Bresenham line between the cells (endpoints excluded)."""
    if (x0, y0) == (x1, y1):
        return True
    line = bresenham_line(x0, y0, x1, y1)
    for x, y in line[1:-1]:
        if grid.is_wall(x, y):
            return False
    return True


def visible_cells(
    grid: Grid, viewer_x: int, viewer_y: int, radius: int | None
) -> frozenset[tuple[int, int]]:
    """Return cells visible to the viewer under the vision rules."""
    own = (viewer_x, viewer_y)
    always: set[tuple[int, int]] = {own}
    for nx, ny in grid.neighbors(viewer_x, viewer_y):
        always.add((nx, ny))

    if radius is None:
        return frozenset(always | set(grid.floor_cells()) | set(grid.walls))

    result: set[tuple[int, int]] = set(always)
    for y in range(grid.height):
        for x in range(grid.width):
            if abs(x - viewer_x) + abs(y - viewer_y) > radius:
                continue
            if (x, y) in always:
                continue
            if has_line_of_sight(grid, viewer_x, viewer_y, x, y):
                result.add((x, y))
    return frozenset(result)


def _revealed_role(
    viewer_role: Role,
    other_role: Role,
    manhattan: int,
    hidden_roles: bool,
    identify_radius: int,
) -> Role | None:
    """Apply hidden-roles rules; zombies never learn which agent is the healer."""
    if not hidden_roles:
        if viewer_role == Role.ZOMBIE and other_role == Role.HEALER:
            return Role.HUMAN
        return other_role
    if manhattan > identify_radius:
        return None
    if viewer_role == Role.ZOMBIE:
        if other_role == Role.HEALER:
            return Role.HUMAN
        return other_role
    return other_role


def observe(
    state: GameState,
    agent_id: int,
    radius: int | None,
    hidden_roles: bool = False,
    identify_radius: int = 2,
    legal: tuple | None = None,
) -> Observation:
    """Build an Observation for agent_id under the given vision settings."""
    from game.rules import legal_actions

    viewer = state.agent(agent_id)
    cells = visible_cells(state.grid, viewer.x, viewer.y, radius)
    visible: list[VisibleAgent] = []
    for other in state.agents:
        if other.id == agent_id:
            continue
        if (other.x, other.y) not in cells:
            continue
        dist = abs(other.x - viewer.x) + abs(other.y - viewer.y)
        role = _revealed_role(
            viewer.role, other.role, dist, hidden_roles, identify_radius
        )
        visible.append(VisibleAgent(id=other.id, x=other.x, y=other.y, role=role))
    legal_tuple = legal if legal is not None else tuple(legal_actions(state, agent_id))
    return Observation(
        self_id=viewer.id,
        self_x=viewer.x,
        self_y=viewer.y,
        self_role=viewer.role,
        self_cooldown=viewer.cooldown,
        round_number=state.round_number,
        rounds_left=max(0, state.max_rounds - state.round_number + 1),
        visible_cells=cells,
        visible_agents=tuple(visible),
        grid=state.grid,
        legal_actions=legal_tuple,
    )

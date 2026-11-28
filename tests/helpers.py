"""Shared builders for unit tests (not a test module itself)."""

from __future__ import annotations

from game.entities import AgentState, Role
from game.grid import Grid
from game.state import GameState


def make_grid(lines: list[str] | str) -> Grid:
    """Build a Grid from map lines."""
    return Grid.from_lines(lines)


def make_state(
    lines: list[str] | str,
    agents: list[AgentState],
    *,
    round_number: int = 1,
    current_index: int = 0,
    skipped: frozenset[int] | None = None,
    acted: frozenset[int] | None = None,
    infections: int = 0,
    heals: int = 0,
    illegal_actions: int = 0,
    max_rounds: int = 60,
    heal_cooldown: int = 3,
) -> GameState:
    """Build a GameState with agents sorted by id."""
    ordered = tuple(sorted(agents, key=lambda a: a.id))
    return GameState(
        grid=make_grid(lines),
        agents=ordered,
        round_number=round_number,
        current_index=current_index,
        skipped=skipped if skipped is not None else frozenset(),
        acted=acted if acted is not None else frozenset(),
        infections=infections,
        heals=heals,
        illegal_actions=illegal_actions,
        max_rounds=max_rounds,
        heal_cooldown=heal_cooldown,
    )


def agent(agent_id: int, role: Role, x: int, y: int, cooldown: int = 0) -> AgentState:
    """Shorthand for AgentState."""
    return AgentState(id=agent_id, role=role, x=x, y=y, cooldown=cooldown)

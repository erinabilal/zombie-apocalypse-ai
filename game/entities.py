"""AgentState record and the Role and Action enums."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Role(Enum):
    """Agent role on the board."""

    ZOMBIE = "zombie"
    HUMAN = "human"
    HEALER = "healer"

    def is_human_team(self) -> bool:
        """Return True if this role counts as human for win conditions."""
        return self in (Role.HUMAN, Role.HEALER)


class Action(IntEnum):
    """Orthogonal actions; STAY does not move or heal."""

    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STAY = 4


# Deltas match Action order: UP, DOWN, LEFT, RIGHT, STAY. Cells are (x, y), origin top-left.
ACTION_DELTAS: dict[Action, tuple[int, int]] = {
    Action.UP: (0, -1),
    Action.DOWN: (0, 1),
    Action.LEFT: (-1, 0),
    Action.RIGHT: (1, 0),
    Action.STAY: (0, 0),
}

MOVE_ACTIONS: tuple[Action, ...] = (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT)


@dataclass(frozen=True)
class AgentState:
    """Immutable snapshot of one agent."""

    id: int
    role: Role
    x: int
    y: int
    cooldown: int = 0

    @property
    def pos(self) -> tuple[int, int]:
        """Return the agent's (x, y) cell."""
        return (self.x, self.y)

    def with_updates(
        self,
        *,
        role: Role | None = None,
        x: int | None = None,
        y: int | None = None,
        cooldown: int | None = None,
    ) -> AgentState:
        """Return a copy with the given fields replaced."""
        return AgentState(
            id=self.id,
            role=self.role if role is None else role,
            x=self.x if x is None else x,
            y=self.y if y is None else y,
            cooldown=self.cooldown if cooldown is None else cooldown,
        )

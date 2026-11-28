"""BaseAgent interface: get_action(obs), reset(), name and per-move stats list."""

from __future__ import annotations

from typing import Any

from game.entities import Action
from game.visibility import Observation


class BaseAgent:
    """Base class for all decision-making agents."""

    def __init__(self, agent_id: int, name: str) -> None:
        """Store id and display name; subclasses may add RNG and config."""
        self.agent_id = agent_id
        self.name = name
        self.stats: list[dict[str, Any]] = []

    def get_action(self, obs: Observation) -> Action:
        """Choose an action from an observation."""
        raise NotImplementedError

    def reset(self) -> None:
        """Clear per-game stats (and any episode state)."""
        self.stats = []

    def _record_stats(self, **kwargs: Any) -> None:
        """Append one per-move stats dict with standard keys defaulting to None/0."""
        entry = {
            "nodes_expanded": kwargs.get("nodes_expanded", 0),
            "nodes_generated": kwargs.get("nodes_generated", 0),
            "time_seconds": kwargs.get("time_seconds", 0.0),
            "path_cost": kwargs.get("path_cost"),
            "depth": kwargs.get("depth"),
        }
        entry.update(kwargs)
        self.stats.append(entry)

"""Game configuration: the frozen GameConfig dataclass, defaults and allowed names."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

AGENT_NAMES: tuple[str, ...] = (
    "manual",
    "random",
    "rulebased",
    "bfs",
    "dfs",
    "ucs",
    "greedy",
    "astar",
    "minimax",
    "alphabeta",
    "expectimax",
    "qlearning",
)
HEURISTIC_NAMES: tuple[str, ...] = ("manhattan", "euclidean", "maze")
OPPONENT_MODELS: tuple[str, ...] = ("random", "adversarial")
MAX_SEARCH_DEPTH: int = 6
WEB_MAX_SEARCH_DEPTH: int = 3


@dataclass(frozen=True)
class GameConfig:
    """Immutable, validated settings for one game."""

    map_text: str
    n_zombies: int = 1
    n_humans: int = 4
    n_healers: int = 1
    max_rounds: int = 60
    heal_cooldown: int = 3
    seed: int = 0
    vision_radius: int | None = None
    hidden_roles: bool = False
    identify_radius: int = 2
    min_spawn_distance: int = 6
    zombie_ai: str = "rulebased"
    human_ai: str = "rulebased"
    healer_ai: str = "rulebased"
    search_depth: int = 2
    move_time_limit: float = 1.0
    node_budget: int | None = None
    heuristic: str = "manhattan"
    relevance_radius: int = 6
    opponent_model: str = "adversarial"
    use_belief_tracker: bool = True
    reward_human_survive_round: float = 0.1
    reward_human_infected: float = -10.0
    reward_human_win: float = 10.0
    reward_zombie_infection: float = 10.0
    reward_zombie_step: float = -0.01
    reward_zombie_win: float = 20.0
    reward_healer_heal: float = 5.0
    reward_healer_infected: float = -10.0
    reward_healer_win: float = 10.0

    def __post_init__(self) -> None:
        """Validate every field and raise ValueError on the first invalid one."""
        if not isinstance(self.map_text, str) or not self.map_text.strip():
            raise ValueError("map_text must be a non-empty string")
        _check_int("n_zombies", self.n_zombies, 1)
        _check_int("n_humans", self.n_humans, 0)
        _check_int("n_healers", self.n_healers, 0)
        if self.n_humans + self.n_healers < 1:
            raise ValueError("need at least one human or healer (n_humans + n_healers >= 1)")
        _check_int("max_rounds", self.max_rounds, 1)
        _check_int("heal_cooldown", self.heal_cooldown, 1)
        _check_int("seed", self.seed, None)
        if self.vision_radius is not None:
            _check_int("vision_radius", self.vision_radius, 1)
        _check_bool("hidden_roles", self.hidden_roles)
        _check_int("identify_radius", self.identify_radius, 0)
        _check_int("min_spawn_distance", self.min_spawn_distance, 0)
        for name in ("zombie_ai", "human_ai", "healer_ai"):
            _check_choice(name, getattr(self, name), AGENT_NAMES)
        _check_int("search_depth", self.search_depth, 1, MAX_SEARCH_DEPTH)
        if (
            isinstance(self.move_time_limit, bool)
            or not isinstance(self.move_time_limit, (int, float))
            or not self.move_time_limit > 0
        ):
            raise ValueError("move_time_limit must be a number > 0")
        if self.node_budget is not None:
            _check_int("node_budget", self.node_budget, 1)
        _check_choice("heuristic", self.heuristic, HEURISTIC_NAMES)
        _check_int("relevance_radius", self.relevance_radius, 1)
        _check_choice("opponent_model", self.opponent_model, OPPONENT_MODELS)
        _check_bool("use_belief_tracker", self.use_belief_tracker)
        for f in fields(self):
            if f.name.startswith("reward_"):
                value = getattr(self, f.name)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"{f.name} must be a number")


DEFAULTS: dict[str, Any] = {
    f.name: f.default for f in fields(GameConfig) if f.name != "map_text"
}


def _check_int(name: str, value: Any, minimum: int | None, maximum: int | None = None) -> None:
    """Raise ValueError unless value is an int (not bool) within [minimum, maximum]."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}, got {value}")


def _check_bool(name: str, value: Any) -> None:
    """Raise ValueError unless value is a bool."""
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false, got {value!r}")


def _check_choice(name: str, value: Any, allowed: tuple[str, ...]) -> None:
    """Raise ValueError unless value is one of the allowed strings."""
    if value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}; got {value!r}")

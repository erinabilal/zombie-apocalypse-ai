"""Definitions of the seven experiments (settings grids and paired seeds)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterator

from config import GameConfig

ROOT = Path(__file__).resolve().parents[1]
MAPS_DIR = ROOT / "maps"

# Agents that are runnable today (qlearning arrives in step 10).
IMPLEMENTED_AGENTS = frozenset(
    {
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
    }
)


@dataclass(frozen=True)
class ExperimentSpec:
    """One named experiment with a short description and setting overrides."""

    name: str
    title: str
    description: str
    group_keys: tuple[str, ...]
    win_side: str  # "zombies" or "humans"
    requires_qlearning: bool = False


EXPERIMENTS: dict[str, ExperimentSpec] = {
    "search_comparison": ExperimentSpec(
        name="search_comparison",
        title="Search comparison",
        description=(
            "Zombie pathfinding AIs (BFS/DFS/UCS/Greedy/A*) vs rule-based humans "
            "on small/medium/large maps: win rate, nodes, time, path cost."
        ),
        group_keys=("map_name", "zombie_ai", "heuristic"),
        win_side="zombies",
    ),
    "healer_ablation": ExperimentSpec(
        name="healer_ablation",
        title="Healer ablation",
        description="0 vs 1 healer with heal cooldown in {1, 3, 5, 10}.",
        group_keys=("n_healers", "heal_cooldown"),
        win_side="humans",
    ),
    "visibility_sweep": ExperimentSpec(
        name="visibility_sweep",
        title="Visibility sweep",
        description=(
            "Vision radius {2, 3, 5, 8, full} with and without the belief tracker."
        ),
        group_keys=("vision_radius", "use_belief_tracker"),
        win_side="humans",
    ),
    "time_limit_sweep": ExperimentSpec(
        name="time_limit_sweep",
        title="Time-limit sweep",
        description="max_rounds in {20, 40, 60, 100}.",
        group_keys=("max_rounds",),
        win_side="humans",
    ),
    "team_size_sweep": ExperimentSpec(
        name="team_size_sweep",
        title="Team-size sweep",
        description="Zombies {1, 2, 3} × humans {4, 6, 8}.",
        group_keys=("n_zombies", "n_humans"),
        win_side="zombies",
    ),
    "adversarial_comparison": ExperimentSpec(
        name="adversarial_comparison",
        title="Adversarial comparison",
        description=(
            "Minimax / alpha-beta / expectimax at depths 1–3 vs random and "
            "rule-based opponents (pruning benefit)."
        ),
        group_keys=("zombie_ai", "search_depth", "human_ai"),
        win_side="zombies",
    ),
    "learned_vs_baselines": ExperimentSpec(
        name="learned_vs_baselines",
        title="Learned vs baselines",
        description=(
            "Q-learning vs random, rule-based, A* and alpha-beta for the same role."
        ),
        group_keys=("zombie_ai",),
        win_side="zombies",
        requires_qlearning=False,
    ),
}


def list_experiments() -> list[str]:
    """Return registered experiment names in stable order."""
    return list(EXPERIMENTS.keys())


def load_map(name: str) -> tuple[str, str]:
    """Load maps/<name>.txt → (map_name, map_text)."""
    path = MAPS_DIR / f"{name}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"map not found: {path}")
    return name, path.read_text(encoding="utf-8")


def base_config(
    map_name: str = "small",
    *,
    seed: int = 0,
    move_time_limit: float = 5.0,
    **overrides: Any,
) -> tuple[GameConfig, str]:
    """Default experiment config (generous time limit for determinism)."""
    name, text = load_map(map_name)
    kwargs: dict[str, Any] = {
        "map_text": text,
        "n_zombies": 1,
        "n_humans": 4,
        "n_healers": 1,
        "max_rounds": 60,
        "heal_cooldown": 3,
        "seed": seed,
        "zombie_ai": "rulebased",
        "human_ai": "rulebased",
        "healer_ai": "rulebased",
        "search_depth": 2,
        "heuristic": "manhattan",
        "use_belief_tracker": True,
        "move_time_limit": move_time_limit,
        "node_budget": 50_000,
    }
    kwargs.update(overrides)
    return GameConfig(**kwargs), name


def iter_settings(experiment: str) -> Iterator[tuple[str, GameConfig, str]]:
    """
    Yield (label, config, map_name) for every cell in the experiment grid.

    Configs use seed=0; the runner replaces seed with base_seed + game_index.
    """
    if experiment not in EXPERIMENTS:
        raise KeyError(f"unknown experiment {experiment!r}; choose one of {list_experiments()}")

    if experiment == "search_comparison":
        search_plain = ("bfs", "dfs", "ucs")
        search_heuristic = ("greedy", "astar")
        heuristics = ("manhattan", "euclidean", "maze")
        for map_name in ("small", "medium", "large"):
            for ai in search_plain:
                cfg, name = base_config(map_name, zombie_ai=ai, heuristic="manhattan")
                yield f"{name}:{ai}", cfg, name
            for ai in search_heuristic:
                for heur in heuristics:
                    cfg, name = base_config(map_name, zombie_ai=ai, heuristic=heur)
                    yield f"{name}:{ai}:{heur}", cfg, name
        return

    if experiment == "healer_ablation":
        for n_healers in (0, 1):
            for cooldown in (1, 3, 5, 10):
                humans = 4 if n_healers == 1 else 5
                cfg, name = base_config(
                    "medium",
                    n_healers=n_healers,
                    n_humans=humans,
                    heal_cooldown=cooldown,
                )
                yield f"healers={n_healers}:cd={cooldown}", cfg, name
        return

    if experiment == "visibility_sweep":
        for radius in (2, 3, 5, 8, None):
            for belief in (True, False):
                label_r = "full" if radius is None else str(radius)
                cfg, name = base_config(
                    "medium",
                    vision_radius=radius,
                    use_belief_tracker=belief,
                    zombie_ai="astar",
                    human_ai="astar",
                    healer_ai="astar",
                )
                yield f"vision={label_r}:belief={belief}", cfg, name
        return

    if experiment == "time_limit_sweep":
        for rounds in (20, 40, 60, 100):
            cfg, name = base_config("medium", max_rounds=rounds)
            yield f"rounds={rounds}", cfg, name
        return

    if experiment == "team_size_sweep":
        for nz in (1, 2, 3):
            for nh in (4, 6, 8):
                cfg, name = base_config("medium", n_zombies=nz, n_humans=nh, n_healers=1)
                yield f"Z{nz}:H{nh}", cfg, name
        return

    if experiment == "adversarial_comparison":
        for ai in ("minimax", "alphabeta", "expectimax"):
            for depth in (1, 2, 3):
                for opp in ("random", "rulebased"):
                    cfg, name = base_config(
                        "small",
                        zombie_ai=ai,
                        human_ai=opp,
                        healer_ai=opp,
                        search_depth=depth,
                        max_rounds=40,
                        node_budget=20_000,
                    )
                    yield f"{ai}:d{depth}:vs={opp}", cfg, name
        return

    if experiment == "learned_vs_baselines":
        for ai in ("qlearning", "random", "rulebased", "astar", "alphabeta"):
            cfg, name = base_config("small", zombie_ai=ai, search_depth=2)
            yield f"zombie={ai}", cfg, name
        return


def with_seed(config: GameConfig, seed: int) -> GameConfig:
    """Return a copy of config with a new seed."""
    return replace(config, seed=seed)

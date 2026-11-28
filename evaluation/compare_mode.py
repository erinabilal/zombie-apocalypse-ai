"""Compare mode: run several AI techniques for one role on paired seeds and summarize."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

from agents.factory import make_agent
from config import GameConfig
from evaluation.metrics import GameRecord, aggregate_by, record_game
from game.engine import Engine, private_rng
from game.entities import Role


def run_one_game(
    config: GameConfig,
    *,
    map_name: str = "",
    label: str = "",
) -> GameRecord:
    """Play one seeded game with agents from GameConfig and return a GameRecord."""
    engine = Engine(config)
    engine.reset()
    assert engine.state is not None
    controllers = {}
    for agent in engine.state.agents:
        if agent.role == Role.ZOMBIE:
            name = config.zombie_ai
        elif agent.role == Role.HEALER:
            name = config.healer_ai
        else:
            name = config.human_ai
        controllers[agent.id] = make_agent(
            name, agent.id, agent.role, config, private_rng(config.seed, agent.id)
        )
    engine.controllers = controllers
    result = engine.run()
    return record_game(config, engine, result, map_name=map_name, label=label)


def compare_agents(
    base: GameConfig,
    agent_names: Sequence[str],
    n_games: int,
    *,
    role: str = "zombie",
    map_name: str = "",
) -> list[dict[str, Any]]:
    """
    Run n_games per agent name, varying one role's AI on paired seeds (base.seed + i).

    Returns aggregate rows suitable for Compare charts / CLI tables.
    """
    role_key = role.lower().strip()
    if role_key not in {"zombie", "human", "healer"}:
        raise ValueError("role must be zombie, human or healer")
    if n_games < 1:
        raise ValueError("n_games must be >= 1")

    records: list[GameRecord] = []
    win_side = "zombies" if role_key == "zombie" else "humans"
    for name in agent_names:
        key = name.lower().strip()
        for i in range(n_games):
            overrides: dict[str, Any] = {"seed": base.seed + i}
            if role_key == "zombie":
                overrides["zombie_ai"] = key
            elif role_key == "human":
                overrides["human_ai"] = key
            else:
                overrides["healer_ai"] = key
            cfg = replace(base, **overrides)
            rec = run_one_game(cfg, map_name=map_name, label=key)
            records.append(rec)

    # Group by the varied AI field for chart-friendly agent column.
    if role_key == "zombie":
        group = ("zombie_ai",)
        agent_field = "zombie_ai"
    elif role_key == "human":
        group = ("human_ai",)
        agent_field = "human_ai"
    else:
        group = ("healer_ai",)
        agent_field = "healer_ai"

    rows = aggregate_by(records, group, win_side=win_side)
    for row in rows:
        row["agent"] = row.pop(agent_field)
        row["compare_role"] = role_key
    return rows


def format_compare_table(rows: Sequence[dict[str, Any]]) -> str:
    """Plain-text table for CLI --compare output."""
    headers = (
        "agent",
        "games",
        "win_rate",
        "win_rate_lo",
        "win_rate_hi",
        "avg_rounds",
        "avg_nodes_expanded",
        "avg_time_per_move",
    )
    lines = ["\t".join(headers)]
    for row in rows:
        cells = []
        for h in headers:
            val = row.get(h, "")
            if isinstance(val, float):
                cells.append(f"{val:.4f}")
            else:
                cells.append(str(val))
        lines.append("\t".join(cells))
    return "\n".join(lines)

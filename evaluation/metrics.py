"""Per-game records, win rate with Wilson 95% interval, mean and standard deviation (stdlib only)."""

from __future__ import annotations

import csv
import math
import statistics
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Iterable, Sequence

from config import GameConfig
from game.engine import Engine, GameResult
from game.entities import Role


@dataclass(frozen=True)
class GameRecord:
    """One finished game with config snapshot and aggregate move stats."""

    map_name: str
    n_zombies: int
    n_humans: int
    n_healers: int
    max_rounds: int
    heal_cooldown: int
    seed: int
    vision_radius: int | None
    hidden_roles: bool
    zombie_ai: str
    human_ai: str
    healer_ai: str
    search_depth: int
    heuristic: str
    use_belief_tracker: bool
    winner: str
    reason: str
    rounds_played: int
    zombies: int
    humans: int
    healers: int
    infections: int
    heals: int
    illegal_actions: int
    survivors: int
    rounds_to_full_infection: int | None
    avg_nodes_expanded: float
    avg_time_per_move: float
    avg_path_cost: float
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        """JSON/CSV-friendly dict (None becomes empty string for CSV)."""
        return asdict(self)


RECORD_FIELDNAMES: tuple[str, ...] = tuple(f.name for f in fields(GameRecord))


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% confidence interval for a binomial proportion."""
    if n <= 0:
        return (0.0, 0.0)
    if successes < 0 or successes > n:
        raise ValueError(f"successes must be in [0, n], got {successes} / {n}")
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    margin = (z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def mean_std(values: Sequence[float]) -> tuple[float, float]:
    """Population-friendly mean and sample std (0 if fewer than 2 values)."""
    nums = [float(v) for v in values]
    if not nums:
        return (0.0, 0.0)
    if len(nums) == 1:
        return (nums[0], 0.0)
    return (statistics.mean(nums), statistics.stdev(nums))


def _move_stats(engine: Engine) -> tuple[float, float, float]:
    """Average nodes, time and path cost over recorded moves that expose stats."""
    nodes = 0.0
    times = 0.0
    costs: list[float] = []
    moves = 0
    for event in engine.history:
        st = event.stats or {}
        if not st:
            continue
        moves += 1
        nodes += float(st.get("nodes_expanded") or 0)
        times += float(st.get("time_seconds") or 0)
        pc = st.get("path_cost")
        if pc is not None:
            costs.append(float(pc))
    if moves == 0:
        return (0.0, 0.0, 0.0)
    avg_cost = statistics.mean(costs) if costs else 0.0
    return (nodes / moves, times / moves, avg_cost)


def _rounds_to_full_infection(engine: Engine) -> int | None:
    """First round where no human-team agents remain, else None."""
    if engine.state is None:
        return None
    if engine.state.count(Role.HUMAN) + engine.state.count(Role.HEALER) > 0:
        return None
    # Reconstruct from history: after an infection wave emptied the human team.
    humans_left = engine.config.n_humans + engine.config.n_healers
    for event in engine.history:
        humans_left -= len(event.newly_infected)
        if event.healed_id is not None:
            humans_left += 1
        if humans_left <= 0:
            return event.round_number
    return engine.result.rounds_played if engine.result else None


def record_game(
    config: GameConfig,
    engine: Engine,
    result: GameResult,
    *,
    map_name: str = "",
    label: str = "",
) -> GameRecord:
    """Build a GameRecord from a finished engine run."""
    avg_nodes, avg_time, avg_cost = _move_stats(engine)
    survivors = result.humans + result.healers
    return GameRecord(
        map_name=map_name or _guess_map_name(config),
        n_zombies=config.n_zombies,
        n_humans=config.n_humans,
        n_healers=config.n_healers,
        max_rounds=config.max_rounds,
        heal_cooldown=config.heal_cooldown,
        seed=config.seed,
        vision_radius=config.vision_radius,
        hidden_roles=config.hidden_roles,
        zombie_ai=config.zombie_ai,
        human_ai=config.human_ai,
        healer_ai=config.healer_ai,
        search_depth=config.search_depth,
        heuristic=config.heuristic,
        use_belief_tracker=config.use_belief_tracker,
        winner=result.winner,
        reason=result.reason,
        rounds_played=result.rounds_played,
        zombies=result.zombies,
        humans=result.humans,
        healers=result.healers,
        infections=result.infections,
        heals=result.heals,
        illegal_actions=result.illegal_actions,
        survivors=survivors,
        rounds_to_full_infection=_rounds_to_full_infection(engine),
        avg_nodes_expanded=avg_nodes,
        avg_time_per_move=avg_time,
        avg_path_cost=avg_cost,
        label=label,
    )


def _guess_map_name(config: GameConfig) -> str:
    """Heuristic map label from dimensions when no name was provided."""
    lines = [ln for ln in config.map_text.splitlines() if ln]
    if not lines:
        return "unknown"
    return f"{len(lines[0])}x{len(lines)}"


def write_records_csv(path: Path | str, records: Iterable[GameRecord]) -> None:
    """Write GameRecords to a CSV file (creates parent dirs)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = list(records)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(RECORD_FIELDNAMES))
        writer.writeheader()
        for rec in rows:
            row = rec.to_dict()
            for key, value in list(row.items()):
                if value is None:
                    row[key] = ""
            writer.writerow(row)


def read_records_csv(path: Path | str) -> list[dict[str, Any]]:
    """Read a metrics CSV into a list of dicts with typed numerics where possible."""
    out: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            out.append(_coerce_row(raw))
    return out


def _coerce_row(raw: dict[str, str]) -> dict[str, Any]:
    """Best-effort type coercion for CSV cells."""
    bool_fields = {"hidden_roles", "use_belief_tracker"}
    int_fields = {
        "n_zombies",
        "n_humans",
        "n_healers",
        "max_rounds",
        "heal_cooldown",
        "seed",
        "search_depth",
        "rounds_played",
        "zombies",
        "humans",
        "healers",
        "infections",
        "heals",
        "illegal_actions",
        "survivors",
        "rounds_to_full_infection",
        "vision_radius",
    }
    float_fields = {"avg_nodes_expanded", "avg_time_per_move", "avg_path_cost"}
    row: dict[str, Any] = dict(raw)
    for key in bool_fields:
        if key in row:
            row[key] = str(row[key]).strip().lower() in {"1", "true", "yes"}
    for key in int_fields:
        if key not in row:
            continue
        text = str(row[key]).strip()
        if text == "":
            row[key] = None
        else:
            row[key] = int(text)
    for key in float_fields:
        if key in row and str(row[key]).strip() != "":
            row[key] = float(row[key])
    return row


def aggregate_by(
    records: Sequence[GameRecord] | Sequence[dict[str, Any]],
    group_keys: Sequence[str],
    *,
    win_side: str = "zombies",
) -> list[dict[str, Any]]:
    """Group records and compute win rate (Wilson), mean rounds/nodes/time."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for rec in records:
        data = rec.to_dict() if isinstance(rec, GameRecord) else dict(rec)
        key = tuple(data.get(k) for k in group_keys)
        groups.setdefault(key, []).append(data)

    rows: list[dict[str, Any]] = []
    for key, items in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        wins = sum(1 for r in items if r.get("winner") == win_side)
        n = len(items)
        lo, hi = wilson_interval(wins, n)
        rounds_m, rounds_s = mean_std([float(r.get("rounds_played") or 0) for r in items])
        nodes_m, nodes_s = mean_std([float(r.get("avg_nodes_expanded") or 0) for r in items])
        time_m, time_s = mean_std([float(r.get("avg_time_per_move") or 0) for r in items])
        row: dict[str, Any] = {k: v for k, v in zip(group_keys, key)}
        row.update(
            {
                "games": n,
                "wins": wins,
                "win_rate": wins / n if n else 0.0,
                "win_rate_lo": lo,
                "win_rate_hi": hi,
                "avg_rounds": rounds_m,
                "std_rounds": rounds_s,
                "avg_nodes_expanded": nodes_m,
                "std_nodes_expanded": nodes_s,
                "avg_time_per_move": time_m,
                "std_time_per_move": time_s,
                "compare_role": "zombie" if win_side == "zombies" else "human",
            }
        )
        rows.append(row)
    return rows

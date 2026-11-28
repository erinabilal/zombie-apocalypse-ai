"""Training CLI: runs Q-learning episodes and writes a learning-curve CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from config import GameConfig
from game.entities import Role
from rl.environment import ZombieEnv
from rl.q_learning import QTable, train_episodes

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "rl" / "models"


def build_parser() -> argparse.ArgumentParser:
    """CLI for `python -m rl.train`."""
    parser = argparse.ArgumentParser(description="Train a tabular Q-learning agent")
    parser.add_argument(
        "--role",
        default="human",
        choices=["zombie", "human", "healer"],
        help="Role the learner controls",
    )
    parser.add_argument("--map", dest="map_path", default="maps/small.txt")
    parser.add_argument("--episodes", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--opponent", default="rulebased")
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--zombies", type=int, default=1)
    parser.add_argument("--humans", type=int, default=4)
    parser.add_argument("--healers", type=int, default=1)
    parser.add_argument("--rounds", type=int, default=60)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Q-table JSON path (default: rl/models/{role}_{map}.json)",
    )
    parser.add_argument(
        "--curve",
        type=Path,
        default=None,
        help="Learning-curve CSV path (default: results/{role}_{map}_curve.csv)",
    )
    return parser


def _load_map(path: str) -> tuple[str, str]:
    """Return (map_stem, map_text)."""
    map_path = Path(path)
    if not map_path.is_file():
        alt = ROOT / path
        if alt.is_file():
            map_path = alt
        else:
            raise FileNotFoundError(f"map not found: {path}")
    return map_path.stem, map_path.read_text(encoding="utf-8")


def train(
    *,
    role: str = "human",
    map_path: str = "maps/small.txt",
    episodes: int = 2000,
    seed: int = 0,
    opponent: str = "rulebased",
    alpha: float = 0.1,
    gamma: float = 0.95,
    n_zombies: int = 1,
    n_humans: int = 4,
    n_healers: int = 1,
    max_rounds: int = 60,
    out: Path | None = None,
    curve_path: Path | None = None,
) -> tuple[Path, Path]:
    """Train and write Q-table + learning curve; return (table_path, curve_path)."""
    map_name, map_text = _load_map(map_path)
    role_enum = Role(role)
    if role_enum == Role.HEALER and n_healers < 1:
        n_healers = 1
    if role_enum == Role.HUMAN and n_humans < 1:
        n_humans = 1
    if role_enum == Role.ZOMBIE and n_zombies < 1:
        n_zombies = 1

    config = GameConfig(
        map_text=map_text,
        n_zombies=n_zombies,
        n_humans=n_humans,
        n_healers=n_healers,
        max_rounds=max_rounds,
        seed=seed,
        zombie_ai=opponent,
        human_ai=opponent,
        healer_ai=opponent,
        move_time_limit=5.0,
        node_budget=20_000,
    )
    env = ZombieEnv(
        config,
        learner_role=role_enum,
        opponent_ai=opponent,
        map_name=map_name,
    )
    table = QTable()
    table.meta = {
        "role": role,
        "map": map_name,
        "episodes": episodes,
        "alpha": alpha,
        "gamma": gamma,
        "opponent": opponent,
        "seed": seed,
    }
    curve = train_episodes(
        env,
        table,
        episodes,
        alpha=alpha,
        gamma=gamma,
        seed=seed,
    )

    out_path = out or (DEFAULT_OUT / f"{role}_{map_name}.json")
    table.save(out_path)

    curve_out = curve_path or (ROOT / "results" / f"{role}_{map_name}_curve.csv")
    curve_out.parent.mkdir(parents=True, exist_ok=True)
    with curve_out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["episode", "return", "epsilon", "winner", "steps"]
        )
        writer.writeheader()
        for row in curve:
            writer.writerow(row)

    # Also dump a small JSON summary for the Results tab.
    summary = {
        "role": role,
        "map": map_name,
        "episodes": episodes,
        "final_avg_return": sum(r["return"] for r in curve[-max(1, len(curve) // 10) :])
        / max(1, len(curve[-max(1, len(curve) // 10) :])),
        "states": len(table.q),
    }
    summary_path = out_path.with_suffix(".meta.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path, curve_out


def main(argv: list[str] | None = None) -> int:
    """CLI entry."""
    args = build_parser().parse_args(argv)
    try:
        table_path, curve_path = train(
            role=args.role,
            map_path=args.map_path,
            episodes=args.episodes,
            seed=args.seed,
            opponent=args.opponent,
            alpha=args.alpha,
            gamma=args.gamma,
            n_zombies=args.zombies,
            n_humans=args.humans,
            n_healers=args.healers,
            max_rounds=args.rounds,
            out=args.out,
            curve_path=args.curve,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {table_path}")
    print(f"wrote {curve_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

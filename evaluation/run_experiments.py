"""CLI that runs a named experiment and writes its CSV to results/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaluation.compare_mode import run_one_game
from evaluation.experiments import (
    EXPERIMENTS,
    IMPLEMENTED_AGENTS,
    iter_settings,
    list_experiments,
    with_seed,
)
from evaluation.metrics import GameRecord, aggregate_by, write_records_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results"


def run_experiment(
    name: str,
    *,
    games: int = 200,
    seed: int = 0,
    out_dir: Path | None = None,
    max_settings: int | None = None,
) -> Path:
    """
    Run every setting of a named experiment with paired seeds and write CSV.

    Returns the path of the written CSV.
    """
    if name not in EXPERIMENTS:
        raise KeyError(f"unknown experiment {name!r}; choose one of {list_experiments()}")
    spec = EXPERIMENTS[name]
    out_dir = out_dir or DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[GameRecord] = []
    settings = list(iter_settings(name))
    if max_settings is not None:
        settings = settings[: max(0, max_settings)]

    for label, cfg, map_name in settings:
        # Skip cells that name unimplemented agents.
        for field in (cfg.zombie_ai, cfg.human_ai, cfg.healer_ai):
            if field not in IMPLEMENTED_AGENTS:
                raise RuntimeError(
                    f"setting {label!r} uses unimplemented agent {field!r}"
                )
        for i in range(games):
            game_cfg = with_seed(cfg, seed + i)
            rec = run_one_game(game_cfg, map_name=map_name, label=label)
            records.append(rec)

    csv_path = out_dir / f"{name}.csv"
    write_records_csv(csv_path, records)

    summary = aggregate_by(records, spec.group_keys, win_side=spec.win_side)
    summary_path = out_dir / f"{name}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return csv_path


def build_parser() -> argparse.ArgumentParser:
    """Argument parser for `python -m evaluation.run_experiments`."""
    parser = argparse.ArgumentParser(description="Run a Zombie Apocalypse AI experiment")
    parser.add_argument(
        "--experiment",
        required=True,
        choices=list_experiments(),
        help="Named experiment from evaluation.experiments",
    )
    parser.add_argument("--games", type=int, default=200, help="Games per setting (paired seeds)")
    parser.add_argument("--seed", type=int, default=0, help="Base seed (game i uses seed+i)")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Directory for CSV / summary JSON (default: results/)",
    )
    parser.add_argument(
        "--max-settings",
        type=int,
        default=None,
        help="Optional cap on settings cells (smoke / baseline runs)",
    )
    parser.add_argument("--list", action="store_true", help="List experiments and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry: run one experiment or list them."""
    parser = build_parser()
    # Allow --list without --experiment.
    if argv is None:
        argv = sys.argv[1:]
    if "--list" in argv:
        for name in list_experiments():
            spec = EXPERIMENTS[name]
            flag = " [needs qlearning]" if spec.requires_qlearning else ""
            print(f"{name}{flag}: {spec.description}")
        return 0
    args = parser.parse_args(argv)
    try:
        path = run_experiment(
            args.experiment,
            games=args.games,
            seed=args.seed,
            out_dir=args.out,
            max_settings=args.max_settings,
        )
    except (KeyError, RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {path}")
    print(f"wrote {path.with_name(path.stem + '_summary.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

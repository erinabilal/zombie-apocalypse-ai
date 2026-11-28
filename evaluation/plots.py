"""Matplotlib figures generated from experiment CSVs (optional dependency)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evaluation.experiments import EXPERIMENTS, list_experiments
from evaluation.metrics import aggregate_by, read_records_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "results"
DEFAULT_FIGURES = DEFAULT_RESULTS / "figures"


def _require_matplotlib():
    """Import pyplot or raise a clear error."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required for plots; install it with: pip install matplotlib"
        ) from exc
    return plt


def _label_row(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Build a short axis label from group keys."""
    parts = []
    for key in keys:
        val = row.get(key)
        if val is None and key == "vision_radius":
            val = "full"
        parts.append(f"{val}")
    return ":".join(parts)


def plot_experiment(
    name: str,
    *,
    results_dir: Path | None = None,
    figures_dir: Path | None = None,
) -> list[Path]:
    """Create win-rate and nodes figures for one experiment; return written paths."""
    if name not in EXPERIMENTS:
        raise KeyError(f"unknown experiment {name!r}")
    spec = EXPERIMENTS[name]
    results_dir = results_dir or DEFAULT_RESULTS
    figures_dir = figures_dir or DEFAULT_FIGURES
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = results_dir / f"{name}.csv"
    summary_path = results_dir / f"{name}_summary.json"
    if summary_path.is_file():
        rows = json.loads(summary_path.read_text(encoding="utf-8"))
    elif csv_path.is_file():
        records = read_records_csv(csv_path)
        rows = aggregate_by(records, spec.group_keys, win_side=spec.win_side)
    else:
        raise FileNotFoundError(f"missing {csv_path} and {summary_path}")

    plt = _require_matplotlib()
    written: list[Path] = []
    labels = [_label_row(r, spec.group_keys) for r in rows]
    win_rates = [float(r["win_rate"]) for r in rows]
    lo = [float(r["win_rate"]) - float(r["win_rate_lo"]) for r in rows]
    hi = [float(r["win_rate_hi"]) - float(r["win_rate"]) for r in rows]
    nodes = [float(r["avg_nodes_expanded"]) for r in rows]
    times = [float(r["avg_time_per_move"]) for r in rows]

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.35), 4))
    x = list(range(len(labels)))
    ax.bar(x, win_rates, yerr=[lo, hi], capsize=3, color="#3ecf8e", edgecolor="#2a9d6a")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Win rate")
    ax.set_title(f"{spec.title} — win rate (Wilson 95%)")
    fig.tight_layout()
    win_path = figures_dir / f"{name}_win_rate.png"
    fig.savefig(win_path, dpi=120)
    plt.close(fig)
    written.append(win_path)

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.35), 4))
    ax.bar(x, nodes, color="#5b8def", edgecolor="#3a6bc7")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("Avg nodes expanded (log)")
    ax.set_title(f"{spec.title} — nodes expanded")
    fig.tight_layout()
    nodes_path = figures_dir / f"{name}_nodes.png"
    fig.savefig(nodes_path, dpi=120)
    plt.close(fig)
    written.append(nodes_path)

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.35), 4))
    ax.bar(x, times, color="#e0a14a", edgecolor="#b87c28")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("Avg time per move (s, log)")
    ax.set_title(f"{spec.title} — time per move")
    fig.tight_layout()
    time_path = figures_dir / f"{name}_time.png"
    fig.savefig(time_path, dpi=120)
    plt.close(fig)
    written.append(time_path)

    return written


def build_parser() -> argparse.ArgumentParser:
    """CLI for `python -m evaluation.plots`."""
    parser = argparse.ArgumentParser(description="Plot experiment CSVs")
    parser.add_argument("--experiment", required=True, choices=list_experiments())
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIGURES)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Generate figures for one experiment."""
    args = build_parser().parse_args(argv)
    try:
        paths = plot_experiment(
            args.experiment, results_dir=args.results, figures_dir=args.figures
        )
    except (KeyError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for path in paths:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

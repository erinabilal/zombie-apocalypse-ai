"""Convert result CSVs / summaries to web/data/results JSON for the Results tab."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.experiments import EXPERIMENTS
from evaluation.metrics import aggregate_by, read_records_csv
RESULTS = ROOT / "results"
WEB_RESULTS = ROOT / "web" / "data" / "results"


def export_one(name: str) -> dict:
    """Export one experiment into web/data/results/ and return an index item."""
    if name not in EXPERIMENTS:
        raise KeyError(f"unknown experiment {name!r}")
    spec = EXPERIMENTS[name]
    WEB_RESULTS.mkdir(parents=True, exist_ok=True)

    summary_path = RESULTS / f"{name}_summary.json"
    csv_path = RESULTS / f"{name}.csv"
    if summary_path.is_file():
        rows = json.loads(summary_path.read_text(encoding="utf-8"))
    elif csv_path.is_file():
        rows = aggregate_by(
            read_records_csv(csv_path), spec.group_keys, win_side=spec.win_side
        )
    else:
        raise FileNotFoundError(f"no CSV/summary for {name}")

    # Chart-friendly agent-like labels.
    for row in rows:
        if "agent" not in row:
            parts = [str(row.get(k, "")) for k in spec.group_keys]
            row["agent"] = ":".join(parts)

    payload = {
        "experiment": name,
        "title": spec.title,
        "description": spec.description,
        "group_keys": list(spec.group_keys),
        "win_side": spec.win_side,
        "rows": rows,
    }
    json_name = f"{name}.json"
    (WEB_RESULTS / json_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    image = None
    fig = RESULTS / "figures" / f"{name}_win_rate.png"
    if fig.is_file():
        dest = WEB_RESULTS / f"{name}_win_rate.png"
        shutil.copy2(fig, dest)
        image = f"./data/results/{name}_win_rate.png"

    return {
        "id": name,
        "title": spec.title,
        "description": spec.description,
        "json": f"./data/results/{json_name}",
        "image": image,
    }


def export_all(names: list[str] | None = None) -> Path:
    """Export selected (or all present) experiments and rewrite index.json."""
    if names is None:
        names = []
        for name in EXPERIMENTS:
            if (RESULTS / f"{name}.csv").is_file() or (
                RESULTS / f"{name}_summary.json"
            ).is_file():
                names.append(name)
    items = []
    for name in names:
        items.append(export_one(name))
    index_path = WEB_RESULTS / "index.json"
    index_path.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    return index_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry for export_results."""
    parser = argparse.ArgumentParser(description="Export experiment results to the web site")
    parser.add_argument(
        "--experiment",
        action="append",
        dest="experiments",
        help="Experiment name (repeatable). Default: all with CSV/summary present.",
    )
    args = parser.parse_args(argv)
    try:
        path = export_all(args.experiments)
    except (KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""One-off helper: export human_small learning curve into web/data/results/."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURVE = ROOT / "results" / "human_small_curve.csv"
OUT = ROOT / "web" / "data" / "results" / "qlearning_curve.json"
INDEX = ROOT / "web" / "data" / "results" / "index.json"


def main() -> int:
    """Write downsampled curve JSON and update index.json."""
    if not CURVE.is_file():
        print(f"missing {CURVE}")
        return 2
    rows = []
    with CURVE.open(encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                {
                    "episode": int(raw["episode"]),
                    "return": float(raw["return"]),
                    "epsilon": float(raw["epsilon"]),
                }
            )
    step = max(1, len(rows) // 100)
    sampled = rows[::step]
    chart_rows = [
        {
            "agent": f"ep{r['episode']}",
            "win_rate": r["return"],
            "avg_rounds": 0.0,
            "avg_nodes_expanded": 0.0,
            "avg_time_per_move": r["epsilon"],
        }
        for r in sampled
    ]
    payload = {
        "experiment": "qlearning_curve",
        "title": "Q-learning learning curve",
        "description": "Human role on small.txt vs rule-based opponents.",
        "rows": chart_rows,
        "curve": sampled,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    index = {"items": []}
    if INDEX.is_file():
        index = json.loads(INDEX.read_text(encoding="utf-8"))
    items = [i for i in index.get("items", []) if i.get("id") != "qlearning_curve"]
    items.append(
        {
            "id": "qlearning_curve",
            "title": payload["title"],
            "description": payload["description"],
            "json": "./data/results/qlearning_curve.json",
            "image": None,
        }
    )
    INDEX.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(sampled)} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

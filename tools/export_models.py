"""Copy trained Q-tables into web/data/models/ for the static site."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "rl" / "models"
WEB_MODELS = ROOT / "web" / "data" / "models"


def export_models(paths: list[Path] | None = None) -> Path:
    """
    Copy Q-table JSON files into web/data/models/ and write index.json.

    Default: every *.json in rl/models/ that is not a *.meta.json.
    """
    WEB_MODELS.mkdir(parents=True, exist_ok=True)
    if paths is None:
        paths = sorted(
            p
            for p in MODELS.glob("*.json")
            if p.is_file() and not p.name.endswith(".meta.json")
        )
    items = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        dest = WEB_MODELS / path.name
        shutil.copy2(path, dest)
        role = "unknown"
        map_name = "unknown"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("meta") or {}
            role = str(meta.get("role", role))
            map_name = str(meta.get("map", map_name))
        except (json.JSONDecodeError, OSError):
            parts = path.stem.split("_")
            if len(parts) >= 2:
                role, map_name = parts[0], parts[1]
        items.append(
            {
                "id": path.stem,
                "role": role,
                "map": map_name,
                "file": f"./data/models/{path.name}",
            }
        )
    index = WEB_MODELS / "index.json"
    index.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    """CLI entry."""
    parser = argparse.ArgumentParser(description="Export Q-tables to the web site")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional specific model JSON files (default: rl/models/*.json)",
    )
    args = parser.parse_args(argv)
    try:
        index = export_models(args.paths or None)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

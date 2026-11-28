"""Build web/py_bundle.zip and web/data/maps.json for the static GitHub Pages site."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
BUNDLE = WEB / "py_bundle.zip"
MAPS_JSON = WEB / "data" / "maps.json"

# Packages and files shipped into the browser (standard-library core only).
PACKAGE_DIRS = ("game", "agents", "search", "adversarial", "rl")
EXTRA_FILES = (
    ROOT / "config.py",
    ROOT / "evaluation" / "__init__.py",
    ROOT / "evaluation" / "metrics.py",
    ROOT / "evaluation" / "compare_mode.py",
    ROOT / "web" / "py_bridge" / "web_api.py",
)


def build_maps_json() -> dict[str, dict[str, object]]:
    """Read maps/*.txt into a JSON-serializable dict."""
    maps: dict[str, dict[str, object]] = {}
    for path in sorted((ROOT / "maps").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        maps[path.stem] = {
            "name": path.stem,
            "text": text,
            "lines": lines,
            "width": len(lines[0]) if lines else 0,
            "height": len(lines),
        }
    return maps


def _add_tree(zf: zipfile.ZipFile, package: str) -> None:
    """Add a package directory to the zip, preserving package paths."""
    base = ROOT / package
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        if path.suffix not in {".py", ".json"} and path.name != ".gitkeep":
            if path.suffix != ".py":
                continue
        if path.name == ".gitkeep":
            continue
        # Skip large model JSON from rl/models in the core bundle (exported separately later).
        if "models" in path.parts and path.suffix == ".json":
            continue
        arcname = path.relative_to(ROOT).as_posix()
        zf.write(path, arcname)


def build_bundle() -> None:
    """Write py_bundle.zip with config, packages, metrics and web_api."""
    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "data").mkdir(parents=True, exist_ok=True)
    if BUNDLE.exists():
        BUNDLE.unlink()
    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for package in PACKAGE_DIRS:
            _add_tree(zf, package)
        for path in EXTRA_FILES:
            if not path.is_file():
                raise FileNotFoundError(path)
            if path.name == "web_api.py":
                # Import as top-level `web_api` inside Pyodide.
                zf.write(path, "web_api.py")
            elif path.parent.name == "evaluation":
                zf.write(path, f"evaluation/{path.name}")
            else:
                zf.write(path, path.name)


def main() -> int:
    """Build maps.json and the Pyodide zip; print a short summary."""
    maps = build_maps_json()
    MAPS_JSON.write_text(json.dumps(maps, indent=2), encoding="utf-8")
    build_bundle()
    size = BUNDLE.stat().st_size
    print(f"wrote {MAPS_JSON.relative_to(ROOT)} ({len(maps)} maps)")
    print(f"wrote {BUNDLE.relative_to(ROOT)} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

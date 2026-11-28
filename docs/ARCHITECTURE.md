# Architecture

## Layers and import direction

Imports only go downward:

```
main.py / web  ->  evaluation  ->  agents  ->  search, adversarial, rl  ->  game
```

`config.py` (`GameConfig`) sits at the repository root and may be imported by every layer, including `game/`.
`game/` never imports pygame, matplotlib, pandas, or any other project package besides `config`.

## Packages

- **`game/`** — `entities`, `grid`, `state`, `rules`, `visibility` (Bresenham LOS, `observe`, hidden roles),
  `engine` (seeded spawn, step/play_round/run, text render), `serialization` (config/state/event/result ↔ JSON).
  Controllers are injected via a Protocol so `game/` never imports `agents/`.
- **`search/`** — pathfinding: BFS, DFS, UCS, Greedy, A*, heuristics.
- **`adversarial/`** — `evaluate` + WEIGHTS, minimax, alpha-beta, expectimax. Agents beyond
  `relevance_radius` are forced to STAY in lookahead (documented approximation).
- **`rl/`** — `ZombieEnv` (one learner, fixed opponents), tabular `QTable` (α=0.1, γ=0.95,
  ε decay 1.0→0.05 over 60% of episodes), `rl.train` CLI, optional self-play stub.
  Discrete state: own cell, clipped enemy offset, neighbor flags, cooldown/time buckets.
- **`agents/`** — Random, RuleBased, Manual, SearchAgent, BeliefTracker, AdversarialAgent, RLAgent,
  and `factory.make_agent`.
- **`evaluation/`** — metrics (GameRecord, Wilson 95%, mean/std, CSV), seven experiment grids,
  `run_experiments` CLI, `compare_mode` (paired seeds), optional matplotlib `plots`.
  Export with `tools/export_results.py` → `web/data/results/`. The Pyodide bundle includes
  `evaluation/metrics.py` and `evaluation/compare_mode.py`.
- **`web/`** — static GitHub Pages site: Pyodide 0.26.4 Worker, Play / Compare / Results / Rules / Help.
  Help copy in `web/data/help.json`; Q-tables in `web/data/models/`. Build with `python tools/build_web.py`.

## Web runtime

`tools/build_web.py` zips the stdlib core into `web/py_bundle.zip` and writes `web/data/maps.json`.
Long jobs (full experiments, RL training) run locally; the site ships exported JSON results and models.
Browser adversarial depth is capped at 3.

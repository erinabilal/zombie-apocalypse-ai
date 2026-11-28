# Architecture

_Skeleton. Filled in as each build step is completed._

## Layers and import direction

Imports only go downward:

```
main.py / web / desktop_ui  ->  evaluation  ->  agents  ->  search, adversarial, rl  ->  game
```

`config.py` (GameConfig) sits at the repository root and may be imported by every layer, including `game/`.
`game/` never imports pygame, matplotlib, pandas, or any other project package besides `config`.

## Packages

- `game/` (step 2 done): `entities`, `grid`, `state`, `rules`, `visibility` (Bresenham LOS,
  `observe`, hidden roles), `engine` (seeded spawn, step/play_round/run, text render),
  `serialization` (config/state/event/result ↔ JSON dicts). Controllers are injected via a
  Protocol so `game/` never imports `agents/`.
- `agents/` (step 5): baselines, `SearchAgent`, `BeliefTracker`, `AdversarialAgent`, `factory`
  (through expectimax). AdversarialAgent rebuilds an approximate GameState from the observation.
- `search/` (step 3): pathfinding algorithms and heuristics.
- `adversarial/` (step 5): `evaluate` + WEIGHTS, minimax, alpha-beta, expectimax. Agents beyond
  `relevance_radius` are treated as STAY (documented approximation).
- `search/`: pathfinding algorithms and heuristics
- `adversarial/`: minimax, alpha-beta, expectimax, evaluation function
- `rl/`: environment, Q-learning, training
- `agents/`: agents built on the above, plus the factory
- `evaluation/`: metrics, experiments, compare mode, plots
- `web/`: static website running the core through Pyodide in a Web Worker

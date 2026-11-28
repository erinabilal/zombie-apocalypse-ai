# Zombie Apocalypse AI

Multi-agent infection and survival in a maze. A turn-based, Pac-Man style grid game where zombies try to
infect every human before the time limit, humans try to survive, and a healer can cure zombies. Every agent
is controlled by an AI technique: uninformed search (BFS, DFS, UCS), informed search (Greedy, A*),
adversarial search (Minimax, Alpha-Beta, Expectimax) and reinforcement learning (Q-learning).

Artificial Intelligence course project by Erina Bilal and Maidah Tariq.

## Live site

**https://erinabilal.github.io/zombie-apocalypse-ai/**

(The repo may need to be **public** for free Pages. Workflow: `.github/workflows/deploy.yml`.)

## Game rules

- **Grid.** Orthogonal moves on a maze. Cells may have terrain costs.
- **Roles.** Zombies infect; humans survive; the healer is on the human team and can cure an adjacent zombie after a cooldown.
- **Infection.** After every action, infection spreads in waves to adjacent human-team agents until stable. A healed agent next to another zombie can be re-infected in the same pass.
- **Heal.** When cooldown allows, a healer action toward an adjacent zombie cures it (no move). Cooldown then resets.
- **Wins.** Early zombie win if no human-team agents remain; early human win if no zombies remain. At the time limit, zombies win only if they strictly outnumber the human team; ties go to humans.
- **Vision.** Optional vision radius and hidden roles; agents use a belief tracker when targets are unseen.
- **Illegal moves.** Blocked or invalid actions become STAY and count as illegal.

## Installation

Requires **Python 3.12+** (developed on 3.14; code stays 3.12-compatible). Core packages use the **standard library only**.

```bash
git clone https://github.com/erinabilal/zombie-apocalypse-ai.git
cd zombie-apocalypse-ai
# optional: python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

Optional for plots only: `pip install matplotlib`

## How to run

### Headless game (CLI)

```bash
python main.py --map maps/small.txt --seed 7 --quiet
python main.py --map maps/small.txt --zombie-ai astar --human-ai rulebased --healer-ai rulebased --heuristic manhattan
python main.py --map maps/small.txt --zombie-ai alphabeta --human-ai random --depth 2
```

AI names: `manual`, `random`, `rulebased`, `bfs`, `dfs`, `ucs`, `greedy`, `astar`,
`minimax`, `alphabeta`, `expectimax`, `qlearning`.

### Compare several AIs

```bash
python main.py --compare --map maps/medium.txt --zombie-ai bfs,dfs,ucs,greedy,astar --games 50
python main.py --compare --compare-role human --human-ai random,rulebased,astar,qlearning --games 20
```

### Browser UI (local)

```bash
python tools/build_web.py
cd web
python -m http.server 8000
```

Open **http://localhost:8000** (do not open `index.html` via `file://`).

Tabs: **Play** (setup, overlays, keyboard manual), **Compare**, **Results**, **Rules**, **Help**.

### Experiments

```bash
python -m evaluation.run_experiments --list
python -m evaluation.run_experiments --experiment healer_ablation --games 200 --seed 0
python -m evaluation.plots --experiment healer_ablation   # needs matplotlib
python tools/export_results.py                           # → web/data/results/
```

### Q-learning

```bash
python -m rl.train --role human --map maps/small.txt --episodes 2000 --out rl/models/human_small.json
python tools/export_models.py                            # → web/data/models/
```

A trained `human_small` table is already shipped under `rl/models/` and `web/data/models/`.

### Tests

```bash
python -m unittest discover -s tests -v
```

## Project structure

```
config.py              GameConfig (frozen, validated)
main.py                CLI headless + --compare
game/                  Engine, rules, grid, visibility, serialization
agents/                Baselines, search, adversarial, RL, factory
search/                BFS/DFS/UCS, Greedy/A*, heuristics
adversarial/           Evaluate, minimax, alpha-beta, expectimax
rl/                    ZombieEnv, Q-learning, train CLI, models/
evaluation/            Metrics, experiments, compare mode, plots
maps/                  small.txt, medium.txt, large.txt
web/                   Static GitHub Pages site (Pyodide Worker)
tools/                 build_web, export_results, export_models
tests/                 unittest suite
docs/                  ARCHITECTURE.md, DECISIONS.md
results/               Experiment CSVs (gitignored); summaries may be local
```

## Authors

Erina Bilal and Maidah Tariq — university AI course project.

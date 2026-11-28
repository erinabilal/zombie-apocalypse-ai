# Zombie Apocalypse AI

Multi-agent infection and survival in a maze. A turn-based, Pac-Man style grid game where zombies try to
infect every human before the time limit, humans try to survive, and a healer can cure zombies. Every agent
is controlled by an AI technique: uninformed search (BFS, DFS, UCS), informed search (Greedy, A*),
adversarial search (Minimax, Alpha-Beta, Expectimax) and reinforcement learning (Q-learning).

University Artificial Intelligence course project by Erina Bilal and Maidah Tariq.

> Status: under construction (build step 2 of 11 — core simulator + baseline agents + CLI).

## Live site

_Link added at deployment: https://erinabilal.github.io/zombie-apocalypse-ai/_

## Game rules

_To be written._

## Installation

_To be written._ Requires Python 3.12 or newer; the core uses only the standard library.

## Commands

```
python main.py --map maps/small.txt --seed 7 --quiet
python main.py --map maps/small.txt --zombie-ai random --human-ai rulebased --healer-ai rulebased
python -m unittest discover -s tests -v
```

Currently supported AI names: `random`, `rulebased`, `bfs`, `dfs`, `ucs`, `greedy`, `astar`,
`minimax`, `alphabeta`, `expectimax` (with `--heuristic` for Greedy/A* and `--depth` for adversarial).
`manual` and `qlearning` come in later steps.

## Project structure

_To be written._

## Screenshots

_To be added._

# Design decisions

Decisions agreed with the project owner, with the reason for each.

1. **Repository layout.** The project lives in the `zombie_apocalypse_ai/` subfolder, which is the Git
   repository root. GitHub remote: `erinabilal/zombie-apocalypse-ai` (nothing is pushed without approval).
2. **Python version.** The brief targets Python 3.12. The development machine has Python 3.14, which is used
   as-is; code must not use any syntax or standard-library feature newer than 3.12, so it also runs under
   Pyodide.
3. **`config.py` in the web bundle.** `tools/build_web.py` also bundles the root `config.py`, because `game/`
   depends on `GameConfig`.
4. **Extra GameConfig fields.** `heuristic` ("manhattan"), `relevance_radius` (6), `opponent_model`
   ("adversarial"), `use_belief_tracker` (True), `node_budget` (None) and the RL reward constants as
   `reward_*` fields.
5. **Time limits and determinism.** Results are deterministic whenever `move_time_limit` is not reached.
   Tests and experiments use a generous limit or a fixed depth; the optional `node_budget` gives a fully
   deterministic cutoff.
6. **Spawn markers.** Map markers (`Z`, `H`, `D`) are used first; extra markers are ignored and missing agents
   are placed randomly with the seeded RNG. The three shipped maps have no markers.
7. **Healer facing a zombie while on cooldown.** That is a move into an occupied cell, so the engine treats
   it as STAY and counts an illegal action. Manual play blocks the input in the UI so the turn is not consumed.
8. **Hidden roles and the healer.** Zombies always see the healer as `HUMAN`, even within `identify_radius`
   and after observing a heal. Humans identify roles normally within the radius.
9. **Validation ranges.** zombies >= 1; humans >= 0; healers >= 0; humans + healers >= 1; rounds >= 1;
   heal cooldown >= 1; vision radius None or >= 1; identify radius >= 0; min spawn distance >= 0;
   search depth 1-6 in the core (the web caps it at 3); move time limit > 0.
10. **Tests.** `tests/test_config.py` is added. The "all three maps load and are connected" test lives in
    `tests/test_grid.py` (step 2a).
11. **Chain infection.** After every action, infection runs in waves until no human-team agent is adjacent to
    a zombie. A newly infected agent can infect its neighbors in the same action.
12. **Heal then re-infect.** A healed agent that stands next to another zombie is re-infected in the same
    action's infection pass. The heal still increments `heals`; the healer should prefer isolated zombies.
13. **Heal directions in legal_actions.** For a healer whose cooldown will be 0 after the turn-start tick
    (`max(0, cooldown - 1) == 0`), directions toward adjacent zombies are included in `legal_actions` so
    RandomAgent can heal. Applying that action heals and does not move.
14. **Belief tracker.** Motion model stay 0.2 / move 0.8 over neighbors; visible agents are point masses;
    visible empty cells get probability 0 for unseen agents; zero mass becomes uniform over non-visible
    floors. `danger_map` weights by `zombie_prob`. SearchAgent uses prey/danger cells when no target is
    visible and `use_belief_tracker` is true (from GameConfig).
15. **Adversarial maximizer.** Each side maximizes `evaluate(state, perspective)` on their own turns;
    opponents minimize it (or are chance nodes under expectimax with `opponent_model=random`).
16. **Relevance radius.** Agents farther than `relevance_radius` from the viewer are forced to STAY in
    the lookahead (approximation noted in ARCHITECTURE.md).
17. **Web bundle.** `tools/build_web.py` zips `game/`, `agents/`, `search/`, `adversarial/`, `rl/`,
    `evaluation/__init__.py`, `evaluation/metrics.py`, `evaluation/compare_mode.py`, root `config.py`,
    and `web_api.py` (top-level in the zip). Pyodide is pinned to **0.26.4** on jsDelivr. Browser
    search depth is capped at 3.
18. **Experiments.** Seven named grids in `evaluation/experiments.py`. Paired seeds use `base_seed + i`.
    CSVs are gitignored under `results/`; JSON exports under `web/data/results/` are committed for the
    site. Plots require optional `matplotlib`; the Results tab charts from exported JSON via Chart.js either way.
19. **Q-learning.** Tabular only (no DQN). State features and rewards follow the brief; human/healer
    learner episodes end on infection. Unseen states fall back to `RuleBasedAgent`. Browser loads
    exported models via `web_api.load_models_json`; without a table, `qlearning` still runs (fallback).

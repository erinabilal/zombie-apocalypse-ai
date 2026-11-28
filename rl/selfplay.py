"""Self-play training (stretch goal): alternate learner roles with shared seeds."""

from __future__ import annotations

from pathlib import Path

from config import GameConfig
from game.entities import Role
from rl.environment import ZombieEnv
from rl.q_learning import QTable, train_episodes

ROOT = Path(__file__).resolve().parents[1]


def train_selfplay(
    map_text: str,
    *,
    episodes_per_role: int = 500,
    seed: int = 0,
    map_name: str = "small",
    out_dir: Path | None = None,
) -> dict[str, Path]:
    """
    Train a short Q-table for each role against rulebased opponents.

    True alternating self-play is a stretch; this writes one table per role.
    """
    out_dir = out_dir or (ROOT / "rl" / "models")
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for role in (Role.HUMAN, Role.ZOMBIE, Role.HEALER):
        config = GameConfig(
            map_text=map_text,
            seed=seed,
            n_zombies=1,
            n_humans=4,
            n_healers=1,
            max_rounds=40,
            move_time_limit=5.0,
            node_budget=20_000,
        )
        env = ZombieEnv(config, learner_role=role, opponent_ai="rulebased", map_name=map_name)
        table = QTable()
        table.meta = {"role": role.value, "map": map_name, "mode": "selfplay_stub"}
        train_episodes(env, table, episodes_per_role, seed=seed)
        path = out_dir / f"{role.value}_{map_name}_selfplay.json"
        table.save(path)
        written[role.value] = path
    return written

"""Tabular Q-learning with epsilon decay and JSON save/load."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterable

from game.entities import Action
from rl.environment import StateKey, ZombieEnv

# Module-level registry for browser / factory lookups: role -> Q-table dict.
_REGISTRY: dict[str, "QTable"] = {}


def register_q_table(role: str, table: "QTable") -> None:
    """Register a Q-table for a role name (zombie/human/healer)."""
    _REGISTRY[role.lower().strip()] = table


def get_registered_q_table(role: str) -> "QTable | None":
    """Return a registered Q-table for the role, if any."""
    return _REGISTRY.get(role.lower().strip())


def clear_registry() -> None:
    """Clear registered Q-tables (tests)."""
    _REGISTRY.clear()


def state_key_to_str(key: StateKey) -> str:
    """Serialize a state tuple for JSON keys."""
    return json.dumps(list(key), separators=(",", ":"))


def state_key_from_str(text: str) -> StateKey:
    """Deserialize a JSON state key."""
    raw = json.loads(text)
    return tuple(tuple(x) if isinstance(x, list) else x for x in raw)


class QTable:
    """Sparse tabular Q(s, a) with greedy / epsilon-greedy policies."""

    def __init__(self, default: float = 0.0) -> None:
        """Create an empty table."""
        self.default = float(default)
        self.q: dict[str, dict[str, float]] = {}
        self.meta: dict[str, Any] = {}

    def get(self, state: StateKey, action: Action) -> float:
        """Return Q(s,a), defaulting to 0."""
        row = self.q.get(state_key_to_str(state))
        if row is None:
            return self.default
        return float(row.get(str(int(action)), self.default))

    def set(self, state: StateKey, action: Action, value: float) -> None:
        """Set Q(s,a)."""
        sk = state_key_to_str(state)
        row = self.q.setdefault(sk, {})
        row[str(int(action))] = float(value)

    def best_action(self, state: StateKey, legal: Iterable[Action]) -> Action:
        """Greedy action among legal; ties broken by Action enum order."""
        actions = list(legal)
        if not actions:
            return Action.STAY
        best = actions[0]
        best_v = self.get(state, best)
        for action in actions[1:]:
            v = self.get(state, action)
            if v > best_v:
                best_v = v
                best = action
        return best

    def max_value(self, state: StateKey, legal: Iterable[Action]) -> float:
        """max_a Q(s,a) over legal actions (0 if none)."""
        actions = list(legal)
        if not actions:
            return 0.0
        return max(self.get(state, a) for a in actions)

    def update(
        self,
        state: StateKey,
        action: Action,
        reward: float,
        next_state: StateKey,
        next_legal: Iterable[Action],
        *,
        alpha: float,
        gamma: float,
        done: bool,
    ) -> float:
        """One Q-learning TD update; returns the new Q value."""
        old = self.get(state, action)
        target = reward if done else reward + gamma * self.max_value(next_state, next_legal)
        new = old + alpha * (target - old)
        self.set(state, action, new)
        return new

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable payload."""
        return {"meta": dict(self.meta), "default": self.default, "q": self.q}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QTable":
        """Load from to_dict payload."""
        table = cls(default=float(data.get("default", 0.0)))
        table.meta = dict(data.get("meta") or {})
        raw_q = data.get("q") or {}
        table.q = {str(k): {str(a): float(v) for a, v in row.items()} for k, row in raw_q.items()}
        return table

    def save(self, path: Path | str) -> None:
        """Write JSON to disk."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> "QTable":
        """Read JSON from disk."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def epsilon_for_episode(episode: int, n_episodes: int, eps_start: float = 1.0, eps_end: float = 0.05) -> float:
    """Linear epsilon decay over the first 60% of episodes, then eps_end."""
    if n_episodes <= 0:
        return eps_end
    decay_eps = max(1, int(0.6 * n_episodes))
    if episode >= decay_eps:
        return eps_end
    t = episode / decay_eps
    return eps_start + t * (eps_end - eps_start)


def select_action(
    table: QTable,
    state: StateKey,
    legal: Iterable[Action],
    rng: random.Random,
    epsilon: float,
) -> Action:
    """Epsilon-greedy action selection."""
    actions = list(legal)
    if not actions:
        return Action.STAY
    if rng.random() < epsilon:
        return rng.choice(actions)
    return table.best_action(state, actions)


def train_episodes(
    env: ZombieEnv,
    table: QTable,
    n_episodes: int,
    *,
    alpha: float = 0.1,
    gamma: float = 0.95,
    seed: int = 0,
    eps_start: float = 1.0,
    eps_end: float = 0.05,
) -> list[dict[str, Any]]:
    """
    Run tabular Q-learning for n_episodes.

    Returns a learning-curve list of {episode, return, epsilon, winner}.
    """
    rng = random.Random(seed)
    curve: list[dict[str, Any]] = []
    for ep in range(n_episodes):
        eps = epsilon_for_episode(ep, n_episodes, eps_start, eps_end)
        state = env.reset(seed=seed + ep)
        total = 0.0
        done = False
        winner = None
        steps = 0
        while not done:
            legal = env.legal_actions()
            action = select_action(table, state, legal, rng, eps)
            next_state, reward, done, info = env.step(action)
            next_legal = () if done else env.legal_actions()
            table.update(
                state,
                action,
                reward,
                next_state,
                next_legal,
                alpha=alpha,
                gamma=gamma,
                done=done,
            )
            total += reward
            state = next_state
            winner = info.get("winner")
            steps += 1
            if steps > 10_000:
                break
        curve.append(
            {
                "episode": ep,
                "return": total,
                "epsilon": eps,
                "winner": winner,
                "steps": steps,
            }
        )
    return curve

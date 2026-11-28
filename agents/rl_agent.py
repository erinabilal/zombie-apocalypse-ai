"""RLAgent: greedy policy from a JSON Q-table with a rule-based fallback for unseen states."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from agents.rule_based_agent import RuleBasedAgent
from game.entities import Action, Role
from game.visibility import Observation
from rl.environment import encode_state
from rl.q_learning import QTable, get_registered_q_table

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = ROOT / "rl" / "models"


class RLAgent(BaseAgent):
    """Greedy Q-table policy; falls back to RuleBasedAgent on empty legal or missing table."""

    def __init__(
        self,
        agent_id: int,
        role: Role,
        rng: random.Random,
        *,
        q_table: QTable | None = None,
        model_path: Path | str | None = None,
        map_name: str = "small",
    ) -> None:
        """Load or accept a Q-table for this role."""
        super().__init__(agent_id, "qlearning")
        self.role = role
        self.rng = rng
        self.fallback = RuleBasedAgent(agent_id, rng)
        self.table = q_table
        if self.table is None:
            registered = get_registered_q_table(role.value)
            if registered is not None:
                self.table = registered
        if self.table is None and model_path is not None:
            path = Path(model_path)
            if path.is_file():
                self.table = QTable.load(path)
        if self.table is None:
            guess = DEFAULT_MODELS / f"{role.value}_{map_name}.json"
            if guess.is_file():
                self.table = QTable.load(guess)
        self._seen = 0
        self._fallback_moves = 0

    def reset(self) -> None:
        """Clear stats for a new game."""
        super().reset()
        self.fallback.reset()
        self._seen = 0
        self._fallback_moves = 0

    def get_action(self, obs: Observation) -> Action:
        """Choose a greedy Q action, or rule-based if the state/table is missing."""
        legal = tuple(obs.legal_actions)
        if not legal:
            action = Action.STAY
            self._record_stats(algorithm="qlearning", fallback=True)
            return action

        if self.table is None:
            action = self.fallback.get_action(obs)
            self._fallback_moves += 1
            self._record_stats(algorithm="qlearning", fallback=True, nodes_expanded=0)
            return action

        from rl.q_learning import state_key_to_str

        state = encode_state(obs)
        if state_key_to_str(state) not in self.table.q:
            action = self.fallback.get_action(obs)
            self._fallback_moves += 1
            self._record_stats(algorithm="qlearning", fallback=True)
            return action

        action = self.table.best_action(state, legal)
        self._seen += 1
        self._record_stats(algorithm="qlearning", fallback=False, nodes_expanded=0)
        return action if action in legal else self.fallback.get_action(obs)

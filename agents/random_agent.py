"""RandomAgent: picks uniformly among legal actions using its private RNG."""

from __future__ import annotations

import random

from agents.base_agent import BaseAgent
from game.entities import Action
from game.visibility import Observation


class RandomAgent(BaseAgent):
    """Uniform random legal action."""

    def __init__(self, agent_id: int, rng: random.Random) -> None:
        """Create a random agent with a private RNG."""
        super().__init__(agent_id, "random")
        self.rng = rng

    def get_action(self, obs: Observation) -> Action:
        """Pick uniformly from legal actions in the observation."""
        legal = list(obs.legal_actions)
        if not legal:
            chosen = Action.STAY
        else:
            chosen = self.rng.choice(legal)
        self._record_stats()
        return chosen

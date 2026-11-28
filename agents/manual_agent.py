"""ManualAgent: actions supplied by a human player (keyboard in the UI)."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from game.entities import Action
from game.visibility import Observation


class ManualAgent(BaseAgent):
    """Placeholder controller; the web/CLI supplies actions via Engine.step(action=...)."""

    def __init__(self, agent_id: int) -> None:
        """Create a manual agent that refuses automatic get_action calls."""
        super().__init__(agent_id, "manual")

    def get_action(self, obs: Observation) -> Action:
        """Raise if the engine asks for an automatic action (use submit_manual_action)."""
        raise RuntimeError("manual agent requires submit_manual_action / step(action=...)")

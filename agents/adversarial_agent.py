"""AdversarialAgent: minimax/alpha-beta/expectimax with iterative deepening and a time limit."""

from __future__ import annotations

import random
import time

from agents.base_agent import BaseAgent
from adversarial._common import AdversarialStats
from adversarial.alphabeta import alphabeta
from adversarial.expectimax import expectimax
from adversarial.minimax import minimax
from game.entities import Action, AgentState, Role
from game.state import GameState
from game.visibility import Observation


class AdversarialAgent(BaseAgent):
    """Looks ahead with adversarial search using an approximate state from the observation."""

    def __init__(
        self,
        agent_id: int,
        algorithm: str,
        rng: random.Random,
        *,
        search_depth: int = 2,
        move_time_limit: float = 1.0,
        node_budget: int | None = None,
        relevance_radius: int = 6,
        opponent_model: str = "adversarial",
        heal_cooldown: int = 3,
    ) -> None:
        """Create an adversarial agent for minimax, alphabeta or expectimax."""
        super().__init__(agent_id, algorithm)
        self.algorithm = algorithm.lower().strip()
        self.rng = rng
        self.search_depth = search_depth
        self.move_time_limit = move_time_limit
        self.node_budget = node_budget
        self.relevance_radius = relevance_radius
        self.opponent_model = opponent_model
        self.heal_cooldown = heal_cooldown

    def get_action(self, obs: Observation) -> Action:
        """Iterative deepening up to search_depth within move_time_limit."""
        state = state_from_observation(obs, self.heal_cooldown)
        perspective = obs.self_role
        # Ensure the reconstructed state is about to act as this agent.
        if state.current_agent() is None or state.current_agent().id != obs.self_id:
            legal = list(obs.legal_actions) or [Action.STAY]
            chosen = self.rng.choice(legal)
            self._record_stats(algorithm=self.algorithm)
            return chosen

        deadline = time.perf_counter() + self.move_time_limit
        best_action: Action | None = None
        last_stats = AdversarialStats(node_budget=self.node_budget)
        last_value = 0.0
        max_depth = max(1, self.search_depth)

        for depth in range(1, max_depth + 1):
            if time.perf_counter() >= deadline:
                break
            stats = AdversarialStats(node_budget=self.node_budget)
            value, action = self._search(state, depth, perspective, obs.self_id, stats)
            last_stats = stats
            last_value = value
            if action is not None:
                best_action = action
            if time.perf_counter() >= deadline or stats.over_budget():
                break

        legal = set(obs.legal_actions)
        if best_action is None or best_action not in legal:
            best_action = self.rng.choice(sorted(legal, key=lambda a: a.value)) if legal else Action.STAY

        self._record_stats(
            nodes_expanded=last_stats.nodes_expanded,
            nodes_generated=last_stats.nodes_generated,
            time_seconds=max(0.0, time.perf_counter() - (deadline - self.move_time_limit)),
            depth=max_depth,
            path_cost=None,
            algorithm=self.algorithm,
            value=last_value,
        )
        return best_action

    def _search(
        self,
        state: GameState,
        depth: int,
        perspective: Role,
        viewer_id: int,
        stats: AdversarialStats,
    ) -> tuple[float, Action | None]:
        """Dispatch to the configured adversarial algorithm."""
        if self.algorithm == "alphabeta":
            return alphabeta(
                state,
                depth,
                perspective,
                viewer_id,
                self.relevance_radius,
                stats,
            )
        if self.algorithm == "expectimax":
            return expectimax(
                state,
                depth,
                perspective,
                viewer_id,
                self.relevance_radius,
                self.opponent_model,
                stats,
            )
        return minimax(
            state,
            depth,
            perspective,
            viewer_id,
            self.relevance_radius,
            stats,
        )


def state_from_observation(obs: Observation, heal_cooldown: int) -> GameState:
    """Rebuild an approximate GameState from a (preferably full-info) observation."""
    agents: list[AgentState] = [
        AgentState(
            id=obs.self_id,
            role=obs.self_role,
            x=obs.self_x,
            y=obs.self_y,
            cooldown=obs.self_cooldown,
        )
    ]
    for other in obs.visible_agents:
        role = other.role if other.role is not None else Role.HUMAN
        agents.append(AgentState(id=other.id, role=role, x=other.x, y=other.y, cooldown=0))
    ordered = tuple(sorted(agents, key=lambda a: a.id))
    index = next(i for i, a in enumerate(ordered) if a.id == obs.self_id)
    acted = frozenset(a.id for a in ordered if a.id < obs.self_id)
    max_rounds = max(obs.round_number, obs.round_number + obs.rounds_left - 1)
    return GameState(
        grid=obs.grid,
        agents=ordered,
        round_number=obs.round_number,
        current_index=index,
        skipped=frozenset(),
        acted=acted,
        infections=0,
        heals=0,
        illegal_actions=0,
        max_rounds=max_rounds,
        heal_cooldown=heal_cooldown,
    )

"""Shared helpers for adversarial search (not part of the public package API)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game.entities import ACTION_DELTAS, Action, Role
from game.rules import advance_turn, apply_action, legal_actions
from game.state import GameState


@dataclass
class AdversarialStats:
    """Mutable counters shared across a search call."""

    nodes_expanded: int = 0
    nodes_generated: int = 0
    node_budget: int | None = None

    def over_budget(self) -> bool:
        """Return True if the optional node budget has been exhausted."""
        return self.node_budget is not None and self.nodes_expanded >= self.node_budget


def is_max_agent(state: GameState, perspective: Role) -> bool:
    """Return True if the acting agent is on perspective's team (they maximize evaluate)."""
    agent = state.current_agent()
    if agent is None:
        return True
    if perspective == Role.ZOMBIE:
        return agent.role == Role.ZOMBIE
    return agent.role.is_human_team()


def agent_within_relevance(
    state: GameState, agent_id: int, viewer_id: int, radius: int
) -> bool:
    """Return True if agent_id is within Manhattan relevance_radius of viewer_id."""
    a = state.agent(agent_id)
    v = state.agent(viewer_id)
    return abs(a.x - v.x) + abs(a.y - v.y) <= radius


def ordered_actions(state: GameState, agent_id: int) -> list[Action]:
    """Order actions: heals first, then moves toward/away from the nearest enemy."""
    legal = legal_actions(state, agent_id)
    agent = state.agent(agent_id)
    heals: list[Action] = []
    others: list[Action] = []

    enemies = []
    if agent.role == Role.ZOMBIE:
        enemies = [a for a in state.agents if a.role.is_human_team()]
    else:
        enemies = [a for a in state.agents if a.role == Role.ZOMBIE]

    for action in legal:
        if agent.role == Role.HEALER and action != Action.STAY:
            dx, dy = ACTION_DELTAS[action]
            tx, ty = agent.x + dx, agent.y + dy
            for other in state.agents:
                if other.role == Role.ZOMBIE and other.x == tx and other.y == ty:
                    if max(0, agent.cooldown - 1) == 0:
                        heals.append(action)
                        break
            else:
                others.append(action)
            continue
        others.append(action)

    def move_key(action: Action) -> tuple:
        dx, dy = ACTION_DELTAS[action]
        nx, ny = agent.x + dx, agent.y + dy
        if not enemies:
            return (0, action.value)
        dist = min(abs(nx - e.x) + abs(ny - e.y) for e in enemies)
        # Zombies prefer smaller distance; humans prefer larger.
        if agent.role == Role.ZOMBIE:
            return (dist, action.value)
        return (-dist, action.value)

    others_sorted = sorted(others, key=move_key)
    # Unique preserve order: heals then others (heals may also be in legal once).
    seen: set[Action] = set()
    ordered: list[Action] = []
    for action in heals + others_sorted:
        if action not in seen:
            seen.add(action)
            ordered.append(action)
    return ordered


def apply_and_advance(
    state: GameState,
    action: Action,
    viewer_id: int,
    relevance_radius: int,
    stats: AdversarialStats,
) -> GameState:
    """Apply the current agent's action (or STAY if far) and advance the turn."""
    agent = state.current_agent()
    if agent is None or state.done:
        return state
    stats.nodes_generated += 1
    if not agent_within_relevance(state, agent.id, viewer_id, relevance_radius):
        chosen = Action.STAY
    else:
        chosen = action
    outcome = apply_action(state, agent.id, chosen)
    return advance_turn(outcome.state)


def successor_states(
    state: GameState,
    viewer_id: int,
    relevance_radius: int,
    stats: AdversarialStats,
) -> list[tuple[Action, GameState]]:
    """Generate (action, next_state) for the current agent under the relevance rule."""
    agent = state.current_agent()
    if agent is None or state.done:
        return []
    if not agent_within_relevance(state, agent.id, viewer_id, relevance_radius):
        nxt = apply_and_advance(state, Action.STAY, viewer_id, relevance_radius, stats)
        return [(Action.STAY, nxt)]
    results: list[tuple[Action, GameState]] = []
    for action in ordered_actions(state, agent.id):
        nxt = apply_and_advance(state, action, viewer_id, relevance_radius, stats)
        results.append((action, nxt))
    return results

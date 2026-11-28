"""Expectimax: random-moving opponents modeled as uniform chance nodes."""

from __future__ import annotations

from game.entities import Action, Role
from game.state import GameState
from adversarial._common import AdversarialStats, is_max_agent, successor_states
from adversarial.evaluation import evaluate
from adversarial.minimax import _minimax


def expectimax(
    state: GameState,
    depth: int,
    perspective: Role,
    viewer_id: int,
    relevance_radius: int = 6,
    opponent_model: str = "random",
    stats: AdversarialStats | None = None,
) -> tuple[float, Action | None]:
    """Return (value, best_action). opponent_model in {random, adversarial}."""
    stats = stats or AdversarialStats()
    if opponent_model == "adversarial":
        return _minimax(
            state, depth, perspective, viewer_id, relevance_radius, stats, root=True
        )
    return _expectimax(
        state, depth, perspective, viewer_id, relevance_radius, stats, root=True
    )


def _expectimax(
    state: GameState,
    depth: int,
    perspective: Role,
    viewer_id: int,
    relevance_radius: int,
    stats: AdversarialStats,
    *,
    root: bool,
) -> tuple[float, Action | None]:
    """Expectimax: our team maximizes evaluate(); opponents are uniform chance nodes."""
    if state.done or depth <= 0 or stats.over_budget():
        return evaluate(state, perspective), None

    stats.nodes_expanded += 1
    successors = successor_states(state, viewer_id, relevance_radius, stats)
    if not successors:
        return evaluate(state, perspective), None

    if is_max_agent(state, perspective):
        best_val = float("-inf")
        best_action: Action | None = None
        for action, nxt in successors:
            val, _ = _expectimax(
                nxt, depth - 1, perspective, viewer_id, relevance_radius, stats, root=False
            )
            if val > best_val:
                best_val = val
                best_action = action
        return best_val, best_action if root else None

    # Chance node: uniform over legal successors.
    total = 0.0
    for _, nxt in successors:
        val, _ = _expectimax(
            nxt, depth - 1, perspective, viewer_id, relevance_radius, stats, root=False
        )
        total += val
    return total / len(successors), None

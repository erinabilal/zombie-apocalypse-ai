"""Alpha-beta pruning with move ordering; returns the same value as minimax."""

from __future__ import annotations

from game.entities import Action, Role
from game.state import GameState
from adversarial._common import AdversarialStats, is_max_agent, successor_states
from adversarial.evaluation import evaluate


def alphabeta(
    state: GameState,
    depth: int,
    perspective: Role,
    viewer_id: int,
    relevance_radius: int = 6,
    stats: AdversarialStats | None = None,
    alpha: float = float("-inf"),
    beta: float = float("inf"),
) -> tuple[float, Action | None]:
    """Return (value, best_action) with alpha-beta pruning."""
    stats = stats or AdversarialStats()
    return _alphabeta(
        state, depth, perspective, viewer_id, relevance_radius, stats, alpha, beta, root=True
    )


def _alphabeta(
    state: GameState,
    depth: int,
    perspective: Role,
    viewer_id: int,
    relevance_radius: int,
    stats: AdversarialStats,
    alpha: float,
    beta: float,
    *,
    root: bool,
) -> tuple[float, Action | None]:
    """Recursive alpha-beta; compares against minimax value with fewer or equal expansions."""
    if state.done or depth <= 0 or stats.over_budget():
        return evaluate(state, perspective), None

    stats.nodes_expanded += 1
    successors = successor_states(state, viewer_id, relevance_radius, stats)
    if not successors:
        return evaluate(state, perspective), None

    maximizing = is_max_agent(state, perspective)
    best_action: Action | None = None

    if maximizing:
        value = float("-inf")
        for action, nxt in successors:
            val, _ = _alphabeta(
                nxt,
                depth - 1,
                perspective,
                viewer_id,
                relevance_radius,
                stats,
                alpha,
                beta,
                root=False,
            )
            if val > value:
                value = val
                best_action = action
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value, best_action if root else None

    value = float("inf")
    for action, nxt in successors:
        val, _ = _alphabeta(
            nxt,
            depth - 1,
            perspective,
            viewer_id,
            relevance_radius,
            stats,
            alpha,
            beta,
            root=False,
        )
        if val < value:
            value = val
            best_action = action
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value, best_action if root else None

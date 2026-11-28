"""Depth-limited minimax over the real turn order (zombies MAX, human team MIN)."""

from __future__ import annotations

from game.entities import Action, Role
from game.state import GameState
from adversarial._common import AdversarialStats, is_max_agent, successor_states
from adversarial.evaluation import evaluate


def minimax(
    state: GameState,
    depth: int,
    perspective: Role,
    viewer_id: int,
    relevance_radius: int = 6,
    stats: AdversarialStats | None = None,
) -> tuple[float, Action | None]:
    """Return (value, best_action_for_root_agent) at the given ply depth."""
    stats = stats or AdversarialStats()
    return _minimax(state, depth, perspective, viewer_id, relevance_radius, stats, root=True)


def _minimax(
    state: GameState,
    depth: int,
    perspective: Role,
    viewer_id: int,
    relevance_radius: int,
    stats: AdversarialStats,
    *,
    root: bool,
) -> tuple[float, Action | None]:
    """Recursive minimax; best_action is set only at the root caller's children."""
    if state.done or depth <= 0 or stats.over_budget():
        return evaluate(state, perspective), None

    stats.nodes_expanded += 1
    successors = successor_states(state, viewer_id, relevance_radius, stats)
    if not successors:
        return evaluate(state, perspective), None

    maximizing = is_max_agent(state, perspective)
    best_action: Action | None = None
    if maximizing:
        best_val = float("-inf")
        for action, nxt in successors:
            val, _ = _minimax(
                nxt, depth - 1, perspective, viewer_id, relevance_radius, stats, root=False
            )
            if val > best_val:
                best_val = val
                best_action = action
        return best_val, best_action if root else None
    best_val = float("inf")
    for action, nxt in successors:
        val, _ = _minimax(
            nxt, depth - 1, perspective, viewer_id, relevance_radius, stats, root=False
        )
        if val < best_val:
            best_val = val
            best_action = action
    return best_val, best_action if root else None

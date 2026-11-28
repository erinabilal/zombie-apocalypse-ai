"""RuleBasedAgent: greedy chase, flee and heal rules for each role."""

from __future__ import annotations

import random
from collections import deque

from agents.base_agent import BaseAgent
from game.entities import ACTION_DELTAS, MOVE_ACTIONS, Action, Role
from game.grid import Grid
from game.visibility import Observation


class RuleBasedAgent(BaseAgent):
    """Role-specific greedy baseline using visible agents only."""

    def __init__(self, agent_id: int, rng: random.Random) -> None:
        """Create a rule-based agent with a private RNG for tie-breaks."""
        super().__init__(agent_id, "rulebased")
        self.rng = rng

    def get_action(self, obs: Observation) -> Action:
        """Choose a chase, flee or heal action from the observation."""
        legal = set(obs.legal_actions)
        if obs.self_role == Role.ZOMBIE:
            chosen = self._zombie_action(obs, legal)
        elif obs.self_role == Role.HEALER:
            chosen = self._healer_action(obs, legal)
        else:
            chosen = self._human_action(obs, legal)
        self._record_stats()
        return chosen

    def _zombie_action(self, obs: Observation, legal: set[Action]) -> Action:
        """Step to the neighbor minimizing terrain-weighted distance to the nearest human."""
        humans = [a for a in obs.visible_agents if a.role in (Role.HUMAN, Role.HEALER)]
        if not humans:
            return self._random_legal(legal)
        return self._best_move(
            obs,
            legal,
            minimize=True,
            score_fn=lambda nx, ny: min(
                _weighted_distance(obs.grid, (nx, ny), (h.x, h.y)) for h in humans
            ),
        )

    def _human_action(self, obs: Observation, legal: set[Action]) -> Action:
        """Step to the neighbor maximizing distance from the nearest zombie."""
        zombies = [a for a in obs.visible_agents if a.role == Role.ZOMBIE]
        if not zombies:
            return self._random_legal(legal)
        return self._best_move(
            obs,
            legal,
            minimize=False,
            score_fn=lambda nx, ny: min(
                _bfs_steps(obs.grid, (nx, ny), (z.x, z.y)) for z in zombies
            ),
        )

    def _healer_action(self, obs: Observation, legal: set[Action]) -> Action:
        """Heal when possible (legal heal dirs), otherwise behave as a human."""
        # legal_actions already includes heal directions when the upcoming tick leaves cooldown at 0.
        for action in MOVE_ACTIONS:
            if action not in legal:
                continue
            dx, dy = ACTION_DELTAS[action]
            tx, ty = obs.self_x + dx, obs.self_y + dy
            for other in obs.visible_agents:
                if other.role == Role.ZOMBIE and other.x == tx and other.y == ty:
                    return action
        return self._human_action(obs, legal)

    def _best_move(
        self,
        obs: Observation,
        legal: set[Action],
        *,
        minimize: bool,
        score_fn,
    ) -> Action:
        """Pick the legal move with best score; STAY is allowed; ties broken by RNG."""
        candidates: list[tuple[float, Action]] = []
        for action in legal:
            dx, dy = ACTION_DELTAS[action]
            nx, ny = obs.self_x + dx, obs.self_y + dy
            score = float(score_fn(nx, ny))
            candidates.append((score, action))
        if not candidates:
            return Action.STAY
        if minimize:
            best = min(c[0] for c in candidates)
        else:
            best = max(c[0] for c in candidates)
        tied = [a for s, a in candidates if s == best]
        return self.rng.choice(tied)

    def _random_legal(self, legal: set[Action]) -> Action:
        """Pick a uniform random legal action."""
        if not legal:
            return Action.STAY
        return self.rng.choice(sorted(legal, key=lambda a: a.value))


def _bfs_steps(grid: Grid, start: tuple[int, int], goal: tuple[int, int]) -> int:
    """Shortest path length in steps, or a large number if unreachable."""
    dist = grid.bfs_distance(start, goal)
    return dist if dist is not None else 10**9


def _weighted_distance(grid: Grid, start: tuple[int, int], goal: tuple[int, int]) -> float:
    """Uniform-cost distance using terrain costs of entered cells."""
    if start == goal:
        return 0.0
    if not grid.is_floor(*start) or not grid.is_floor(*goal):
        return float(10**9)
    best: dict[tuple[int, int], float] = {start: 0.0}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        cx, cy = queue.popleft()
        base = best[(cx, cy)]
        for nx, ny in grid.neighbors(cx, cy):
            cost = base + grid.cost(nx, ny)
            if cost < best.get((nx, ny), float("inf")):
                best[(nx, ny)] = cost
                queue.append((nx, ny))
    return best.get(goal, float(10**9))

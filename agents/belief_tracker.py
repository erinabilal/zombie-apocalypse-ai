"""BeliefTracker: probability maps over cells for agents that are not currently visible."""

from __future__ import annotations

import math
from typing import Iterable

from game.entities import Role
from game.grid import Grid
from game.visibility import Observation, VisibleAgent

Cell = tuple[int, int]
STAY_PROB = 0.2
MOVE_PROB = 0.8


class BeliefTracker:
    """Per-agent cell distributions with a simple motion model and optional role beliefs."""

    def __init__(
        self,
        grid: Grid,
        self_id: int,
        *,
        hidden_roles: bool = False,
    ) -> None:
        """Create an empty tracker for one observing agent."""
        self.grid = grid
        self.self_id = self_id
        self.hidden_roles = hidden_roles
        self.floors: tuple[Cell, ...] = tuple(grid.floor_cells())
        self.beliefs: dict[int, dict[Cell, float]] = {}
        self.zombie_prob: dict[int, float] = {}
        self.last_role: dict[int, Role | None] = {}

    def update(self, obs: Observation) -> None:
        """Predict motion then assimilate the current observation."""
        visible_ids = {a.id for a in obs.visible_agents}
        # Ensure every currently visible other agent is tracked.
        for agent in obs.visible_agents:
            self._ensure_agent(agent.id)
            self._update_role_belief(agent)

        # Also keep tracking agents we have seen before but not now.
        tracked = set(self.beliefs.keys())

        for agent_id in tracked:
            if agent_id == self.self_id:
                continue
            self._predict(agent_id)
            if agent_id in visible_ids:
                pos = next((a.x, a.y) for a in obs.visible_agents if a.id == agent_id)
                self._set_point_mass(agent_id, pos)
            else:
                self._zero_visible_cells(agent_id, obs.visible_cells)
                self._renormalize(agent_id, obs.visible_cells)

        # Visible empty cells: already zeroed for unseen agents; point masses handle seen ones.

    def most_likely_cell(self, agent_id: int) -> Cell | None:
        """Return the mode of the belief for agent_id, or None if unknown."""
        dist = self.beliefs.get(agent_id)
        if not dist:
            return None
        return max(dist.items(), key=lambda kv: (kv[1], -kv[0][1], -kv[0][0]))[0]

    def danger_map(self) -> dict[Cell, float]:
        """Return per-cell danger = sum_i belief_i(cell) * P(i is zombie)."""
        danger: dict[Cell, float] = {c: 0.0 for c in self.floors}
        for agent_id, dist in self.beliefs.items():
            weight = self.zombie_prob.get(agent_id, 0.0)
            if weight <= 0.0:
                continue
            for cell, p in dist.items():
                danger[cell] = danger.get(cell, 0.0) + weight * p
        return danger

    def entropy(self, agent_id: int) -> float:
        """Return Shannon entropy (bits) of the belief over cells for agent_id."""
        dist = self.beliefs.get(agent_id)
        if not dist:
            return 0.0
        h = 0.0
        for p in dist.values():
            if p > 0.0:
                h -= p * math.log2(p)
        return h

    def prey_cells(self, top_k: int = 3) -> list[Cell]:
        """Most likely cells of agents believed to be human-team (for zombie chase)."""
        scored: list[tuple[float, Cell]] = []
        for agent_id, dist in self.beliefs.items():
            human_weight = 1.0 - self.zombie_prob.get(agent_id, 0.0)
            if human_weight <= 0.0:
                continue
            cell = self.most_likely_cell(agent_id)
            if cell is None:
                continue
            p = dist.get(cell, 0.0) * human_weight
            scored.append((p, cell))
        scored.sort(key=lambda t: (-t[0], t[1][1], t[1][0]))
        return [c for _, c in scored[:top_k]]

    def danger_sources(self, threshold: float = 0.05) -> list[Cell]:
        """Cells with danger at or above threshold, highest first (for human flee)."""
        danger = self.danger_map()
        cells = [(p, c) for c, p in danger.items() if p >= threshold]
        cells.sort(key=lambda t: (-t[0], t[1][1], t[1][0]))
        return [c for _, c in cells[:8]]

    def _ensure_agent(self, agent_id: int) -> None:
        """Create a uniform prior over floor cells if this agent is new."""
        if agent_id in self.beliefs:
            return
        n = len(self.floors)
        prior = 1.0 / n if n else 0.0
        self.beliefs[agent_id] = {c: prior for c in self.floors}
        self.zombie_prob.setdefault(agent_id, 0.5 if self.hidden_roles else 0.0)
        self.last_role.setdefault(agent_id, None)

    def _update_role_belief(self, agent: VisibleAgent) -> None:
        """Update zombie probability from an observed role (and mark last role)."""
        self.last_role[agent.id] = agent.role
        if agent.role == Role.ZOMBIE:
            self.zombie_prob[agent.id] = 1.0
        elif agent.role in (Role.HUMAN, Role.HEALER):
            self.zombie_prob[agent.id] = 0.0
        elif agent.role is None and self.hidden_roles:
            # Mild evidence: unknown role keeps prior; nudge from proximity later if needed.
            self.zombie_prob.setdefault(agent.id, 0.5)

    def note_infection(self, agent_id: int) -> None:
        """Mark an agent as a zombie after observing an infection involving them."""
        self._ensure_agent(agent_id)
        self.zombie_prob[agent_id] = 1.0
        self.last_role[agent_id] = Role.ZOMBIE

    def _predict(self, agent_id: int) -> None:
        """Apply the stay/move motion model to one agent's distribution."""
        old = self.beliefs[agent_id]
        new: dict[Cell, float] = {c: 0.0 for c in self.floors}
        for cell, mass in old.items():
            if mass <= 0.0:
                continue
            new[cell] += STAY_PROB * mass
            neighbors = self.grid.neighbors(*cell)
            if not neighbors:
                new[cell] += MOVE_PROB * mass
                continue
            share = MOVE_PROB * mass / len(neighbors)
            for nxt in neighbors:
                new[nxt] += share
        self.beliefs[agent_id] = new

    def _set_point_mass(self, agent_id: int, cell: Cell) -> None:
        """Collapse the belief to a single observed cell."""
        self.beliefs[agent_id] = {c: (1.0 if c == cell else 0.0) for c in self.floors}

    def _zero_visible_cells(self, agent_id: int, visible: Iterable[Cell]) -> None:
        """Set probability to 0 on every visible cell (unseen agent cannot be there)."""
        dist = self.beliefs[agent_id]
        for cell in visible:
            if cell in dist:
                dist[cell] = 0.0

    def _renormalize(self, agent_id: int, visible: frozenset[Cell]) -> None:
        """Renormalize; if mass is zero, use uniform over non-visible floor cells."""
        dist = self.beliefs[agent_id]
        total = sum(dist.values())
        if total > 0.0:
            self.beliefs[agent_id] = {c: p / total for c, p in dist.items()}
            return
        hidden = [c for c in self.floors if c not in visible]
        if not hidden:
            # Everywhere visible and empty: fall back to uniform over all floors.
            n = len(self.floors)
            self.beliefs[agent_id] = {c: 1.0 / n for c in self.floors} if n else {}
            return
        mass = 1.0 / len(hidden)
        self.beliefs[agent_id] = {c: (mass if c in hidden else 0.0) for c in self.floors}

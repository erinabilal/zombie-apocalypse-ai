"""Unit tests for BeliefTracker."""

from __future__ import annotations

import unittest

from agents.belief_tracker import BeliefTracker
from game.entities import Action, Role
from game.grid import Grid
from game.visibility import Observation, VisibleAgent, visible_cells


def _obs(
    grid: Grid,
    self_id: int,
    x: int,
    y: int,
    role: Role,
    others: list[VisibleAgent],
    radius: int | None = None,
) -> Observation:
    """Build a minimal Observation for belief updates."""
    cells = visible_cells(grid, x, y, radius)
    visible_others = tuple(a for a in others if (a.x, a.y) in cells)
    return Observation(
        self_id=self_id,
        self_x=x,
        self_y=y,
        self_role=role,
        self_cooldown=0,
        round_number=1,
        rounds_left=60,
        visible_cells=cells,
        visible_agents=visible_others,
        grid=grid,
        legal_actions=(Action.STAY,),
    )


class TestBeliefTracker(unittest.TestCase):
    """Probability mass, visibility constraints and helpers."""

    def setUp(self) -> None:
        """Open room used by most cases."""
        self.grid = Grid.from_lines(
            [
                "#######",
                "#.....#",
                "#.....#",
                "#.....#",
                "#######",
            ]
        )

    def test_probabilities_sum_to_one(self) -> None:
        """After each update, every tracked agent's mass sums to 1."""
        tracker = BeliefTracker(self.grid, self_id=0)
        other = VisibleAgent(id=1, x=5, y=1, role=Role.HUMAN)
        obs = _obs(self.grid, 0, 1, 1, Role.ZOMBIE, [other], radius=1)
        tracker.update(obs)
        # Agent 1 is not visible (far); still tracked only if seen — first update with
        # limited radius may not include them. Seed by a full-vision sighting first.
        tracker = BeliefTracker(self.grid, self_id=0)
        obs_full = _obs(self.grid, 0, 1, 1, Role.ZOMBIE, [other], radius=None)
        tracker.update(obs_full)
        total = sum(tracker.beliefs[1].values())
        self.assertAlmostEqual(total, 1.0, places=9)

        # Force unseen: pass empty visible_agents but keep tracker state for id 1.
        obs_unseen = Observation(
            self_id=0,
            self_x=1,
            self_y=3,
            self_role=Role.ZOMBIE,
            self_cooldown=0,
            round_number=2,
            rounds_left=59,
            visible_cells=visible_cells(self.grid, 1, 3, 1),
            visible_agents=(),
            grid=self.grid,
            legal_actions=(Action.STAY,),
        )
        tracker.update(obs_unseen)
        self.assertAlmostEqual(sum(tracker.beliefs[1].values()), 1.0, places=9)

    def test_visible_agent_is_point_mass(self) -> None:
        """A visible agent collapses to probability 1 on its cell."""
        tracker = BeliefTracker(self.grid, self_id=0)
        other = VisibleAgent(id=1, x=3, y=2, role=Role.HUMAN)
        tracker.update(_obs(self.grid, 0, 1, 1, Role.ZOMBIE, [other], radius=None))
        dist = tracker.beliefs[1]
        self.assertAlmostEqual(dist[(3, 2)], 1.0)
        self.assertAlmostEqual(sum(v for c, v in dist.items() if c != (3, 2)), 0.0)

    def test_visible_empty_cells_get_zero_when_unseen(self) -> None:
        """Unseen agents have probability 0 on every currently visible cell."""
        tracker = BeliefTracker(self.grid, self_id=0)
        other = VisibleAgent(id=1, x=5, y=3, role=Role.ZOMBIE)
        tracker.update(_obs(self.grid, 0, 1, 1, Role.HUMAN, [other], radius=None))
        # Now hide them: visible neighborhood around (1,1) must be zero for id 1.
        cells = visible_cells(self.grid, 1, 1, 2)
        obs = Observation(
            self_id=0,
            self_x=1,
            self_y=1,
            self_role=Role.HUMAN,
            self_cooldown=0,
            round_number=2,
            rounds_left=58,
            visible_cells=cells,
            visible_agents=(),
            grid=self.grid,
            legal_actions=(Action.STAY,),
        )
        tracker.update(obs)
        for cell in cells:
            if self.grid.is_floor(*cell):
                self.assertEqual(tracker.beliefs[1].get(cell, 0.0), 0.0)
        self.assertAlmostEqual(sum(tracker.beliefs[1].values()), 1.0, places=9)

    def test_most_likely_and_entropy(self) -> None:
        """most_likely_cell matches the mode; entropy is 0 for a point mass."""
        tracker = BeliefTracker(self.grid, self_id=0)
        other = VisibleAgent(id=1, x=2, y=2, role=Role.HUMAN)
        tracker.update(_obs(self.grid, 0, 1, 1, Role.ZOMBIE, [other], radius=None))
        self.assertEqual(tracker.most_likely_cell(1), (2, 2))
        self.assertAlmostEqual(tracker.entropy(1), 0.0, places=9)

    def test_danger_map_uses_zombie_prob(self) -> None:
        """danger_map weights beliefs by zombie probability."""
        tracker = BeliefTracker(self.grid, self_id=0, hidden_roles=True)
        z = VisibleAgent(id=1, x=4, y=2, role=Role.ZOMBIE)
        tracker.update(_obs(self.grid, 0, 1, 1, Role.HUMAN, [z], radius=None))
        danger = tracker.danger_map()
        self.assertAlmostEqual(danger[(4, 2)], 1.0)
        self.assertEqual(tracker.zombie_prob[1], 1.0)

    def test_motion_spreads_mass(self) -> None:
        """After becoming unseen, probability spreads beyond the last seen cell."""
        tracker = BeliefTracker(self.grid, self_id=0)
        other = VisibleAgent(id=1, x=3, y=2, role=Role.HUMAN)
        tracker.update(_obs(self.grid, 0, 1, 1, Role.ZOMBIE, [other], radius=None))
        cells = visible_cells(self.grid, 1, 1, 1)
        obs = Observation(
            self_id=0,
            self_x=1,
            self_y=1,
            self_role=Role.ZOMBIE,
            self_cooldown=0,
            round_number=2,
            rounds_left=58,
            visible_cells=cells,
            visible_agents=(),
            grid=self.grid,
            legal_actions=(Action.STAY,),
        )
        tracker.update(obs)
        # Last cell (3,2) is not visible at radius 1 from (1,1); mass may remain there
        # plus neighbors. Ensure more than one cell has mass.
        positive = sum(1 for p in tracker.beliefs[1].values() if p > 1e-12)
        self.assertGreater(positive, 1)


if __name__ == "__main__":
    unittest.main()

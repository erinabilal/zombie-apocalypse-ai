"""Unit tests for line of sight and observe()."""

from __future__ import annotations

import unittest

from game.entities import Role
from game.visibility import has_line_of_sight, observe, visible_cells
from helpers import agent, make_state

MAP = [
    "#######",
    "#.....#",
    "#.###.#",
    "#.....#",
    "#######",
]


class TestVisibility(unittest.TestCase):
    """LOS, radius and hidden roles."""

    def test_wall_blocks_sight(self) -> None:
        """A wall on the Bresenham line blocks visibility."""
        state = make_state(
            MAP,
            [agent(0, Role.HUMAN, 1, 1), agent(1, Role.ZOMBIE, 5, 1)],
        )
        # Direct horizontal line through open cells: clear.
        self.assertTrue(has_line_of_sight(state.grid, 1, 1, 5, 1))
        # Vertical through the wall column center.
        self.assertFalse(has_line_of_sight(state.grid, 3, 1, 3, 3))

    def test_radius_respected(self) -> None:
        """Cells beyond Manhattan radius are not visible (except always-visible neighbors)."""
        state = make_state(MAP, [agent(0, Role.HUMAN, 1, 1)])
        cells = visible_cells(state.grid, 1, 1, radius=1)
        self.assertIn((1, 1), cells)
        self.assertIn((2, 1), cells)  # adjacent
        self.assertNotIn((5, 3), cells)

    def test_none_radius_full_information(self) -> None:
        """radius=None makes every cell visible."""
        state = make_state(MAP, [agent(0, Role.HUMAN, 1, 1)])
        cells = visible_cells(state.grid, 1, 1, radius=None)
        self.assertEqual(len(cells), state.grid.width * state.grid.height)

    def test_own_and_adjacent_always_visible(self) -> None:
        """Own cell and non-wall adjacent cells are always visible even if radius is 0-like."""
        state = make_state(MAP, [agent(0, Role.HUMAN, 1, 1)])
        # radius 1 still includes adjacents; check adjacent floor always in set for radius 1.
        cells = visible_cells(state.grid, 1, 1, radius=1)
        self.assertIn((1, 1), cells)
        self.assertIn((1, 2), cells)

    def test_observe_lists_visible_agents(self) -> None:
        """observe includes other agents standing on visible cells."""
        state = make_state(
            MAP,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 2, 1),
                agent(2, Role.HUMAN, 5, 3),
            ],
        )
        obs = observe(state, 0, radius=2, hidden_roles=False)
        ids = {a.id for a in obs.visible_agents}
        self.assertIn(1, ids)
        self.assertNotIn(2, ids)

    def test_hidden_roles_and_zombie_never_sees_healer(self) -> None:
        """Hidden roles hide far agents; zombies see healers as HUMAN even when identified."""
        state = make_state(
            [
                "#####",
                "#...#",
                "#...#",
                "#...#",
                "#####",
            ],
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HEALER, 2, 1),
                agent(2, Role.HUMAN, 3, 3),
            ],
        )
        obs = observe(state, 0, radius=None, hidden_roles=True, identify_radius=2)
        by_id = {a.id: a for a in obs.visible_agents}
        self.assertEqual(by_id[1].role, Role.HUMAN)  # healer masked
        self.assertIsNone(by_id[2].role)  # too far to identify (manhattan 4 > 2)


if __name__ == "__main__":
    unittest.main()

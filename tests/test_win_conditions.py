"""Unit tests for win conditions and healer counting as human."""

from __future__ import annotations

import unittest
from dataclasses import replace

from game.entities import Action, Role
from game.rules import advance_turn, apply_action, winner
from helpers import agent, make_state

OPEN = [
    "#######",
    "#.....#",
    "#.....#",
    "#.....#",
    "#######",
]


class TestWinConditions(unittest.TestCase):
    """Win checks after actions and at round end."""

    def test_early_zombie_win_all_infected(self) -> None:
        """No human-team agents left: zombies win with reason all_infected."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 2, 1),
            ],
        )
        out = apply_action(state, 0, Action.STAY)
        self.assertTrue(out.state.done)
        self.assertEqual(out.state.winner, "zombies")
        self.assertEqual(out.state.reason, "all_infected")
        self.assertEqual(winner(out.state), ("zombies", "all_infected"))

    def test_early_human_win_no_zombies(self) -> None:
        """Healing the last zombie: humans win with reason no_zombies."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 2, 1),
                agent(1, Role.HEALER, 1, 1, cooldown=0),
            ],
            current_index=1,
            heal_cooldown=3,
        )
        out = apply_action(state, 1, Action.RIGHT)
        self.assertTrue(out.state.done)
        self.assertEqual(out.state.winner, "humans")
        self.assertEqual(out.state.reason, "no_zombies")

    def test_healer_counts_as_human_for_wins(self) -> None:
        """A lone healer still counts as human-team for all_infected / time_limit."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HEALER, 5, 2),
            ],
            max_rounds=1,
        )
        # Not adjacent: no early infection win.
        out = apply_action(state, 0, Action.STAY)
        self.assertFalse(out.state.done)
        self.assertEqual(out.state.count_human_team(), 1)

    def test_time_limit_tie_goes_to_humans(self) -> None:
        """After the final round, equal counts: humans win (time_limit)."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 5, 2),
            ],
            max_rounds=1,
            round_number=1,
        )
        out = apply_action(state, 0, Action.STAY)
        nxt = advance_turn(out.state)
        # Agent 1 still to act in round 1.
        self.assertFalse(nxt.done)
        out2 = apply_action(nxt, 1, Action.STAY)
        end = advance_turn(out2.state)
        self.assertTrue(end.done)
        self.assertEqual(end.winner, "humans")
        self.assertEqual(end.reason, "time_limit")

    def test_time_limit_zombies_win_when_strictly_more(self) -> None:
        """After the final round, zombies win only if zombies > humans."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.ZOMBIE, 1, 2),
                agent(2, Role.HUMAN, 5, 2),
            ],
            max_rounds=1,
            round_number=1,
        )
        # Play through all three agents staying far apart.
        s = state
        for agent_id in (0, 1, 2):
            s = replace(s, current_index=s.agent_index(agent_id))
            out = apply_action(s, agent_id, Action.STAY)
            s = advance_turn(out.state)
        self.assertTrue(s.done)
        self.assertEqual(s.winner, "zombies")
        self.assertEqual(s.reason, "time_limit")

    def test_healer_surviving_counts_in_time_limit(self) -> None:
        """Healer alone vs one zombie at time limit: tie => humans win."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HEALER, 5, 2),
            ],
            max_rounds=1,
            round_number=1,
        )
        out0 = apply_action(state, 0, Action.STAY)
        s = advance_turn(out0.state)
        out1 = apply_action(s, 1, Action.STAY)
        end = advance_turn(out1.state)
        self.assertEqual(end.winner, "humans")
        self.assertEqual(end.reason, "time_limit")


if __name__ == "__main__":
    unittest.main()

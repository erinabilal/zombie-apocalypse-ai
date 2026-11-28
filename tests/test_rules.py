"""Unit tests for infection, healing, cooldown, illegal moves and apply_action purity."""

from __future__ import annotations

import copy
import unittest

from game.entities import Action, Role
from game.rules import advance_turn, apply_action, infection_targets, legal_actions
from helpers import agent, make_state

OPEN = [
    "#######",
    "#.....#",
    "#.....#",
    "#.....#",
    "#.....#",
    "#.....#",
    "#######",
]


class TestRules(unittest.TestCase):
    """Core rules behavior."""

    def test_adjacency_infection(self) -> None:
        """A zombie infects an orthogonally adjacent human after its action."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 3, 1),
            ],
        )
        # Move right next to the human.
        out = apply_action(state, 0, Action.RIGHT)
        self.assertEqual(out.state.agent(0).pos, (2, 1))
        self.assertEqual(out.state.agent(1).role, Role.ZOMBIE)
        self.assertEqual(out.newly_infected, (1,))
        self.assertEqual(out.event_type, "infect")
        self.assertEqual(out.state.infections, 1)

    def test_infection_after_human_steps_next_to_zombie(self) -> None:
        """A human stepping next to a zombie is infected immediately."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 3, 1),
            ],
            current_index=1,
        )
        out = apply_action(state, 1, Action.LEFT)
        self.assertEqual(out.state.agent(1).role, Role.ZOMBIE)
        self.assertEqual(out.newly_infected, (1,))

    def test_one_action_infects_several(self) -> None:
        """One zombie action can infect multiple adjacent humans."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 2, 2),
                agent(1, Role.HUMAN, 2, 1),
                agent(2, Role.HUMAN, 3, 2),
                agent(3, Role.HUMAN, 5, 5),
            ],
        )
        out = apply_action(state, 0, Action.STAY)
        self.assertEqual(set(out.newly_infected), {1, 2})
        self.assertEqual(out.state.agent(3).role, Role.HUMAN)
        self.assertEqual(out.state.infections, 2)

    def test_chain_infection(self) -> None:
        """A newly infected agent immediately infects its adjacent humans in the same action."""
        # Z - H1 - H2 in a row; Z stays, infects H1, which then infects H2.
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 2, 1),
                agent(2, Role.HUMAN, 3, 1),
            ],
        )
        out = apply_action(state, 0, Action.STAY)
        self.assertEqual(out.state.agent(1).role, Role.ZOMBIE)
        self.assertEqual(out.state.agent(2).role, Role.ZOMBIE)
        self.assertEqual(out.newly_infected, (1, 2))
        self.assertEqual(out.state.infections, 2)

    def test_skip_infected_agent(self) -> None:
        """An agent infected before its turn is skipped for the rest of the round."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 2, 1),
                agent(2, Role.HUMAN, 5, 5),
            ],
        )
        out = apply_action(state, 0, Action.STAY)
        self.assertIn(1, out.state.skipped)
        nxt = advance_turn(out.state)
        self.assertEqual(nxt.current_agent().id, 2)

    def test_heal_converts_zombie_to_human(self) -> None:
        """Healer facing an adjacent zombie with cooldown 0 heals and does not move."""
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
        self.assertEqual(out.healed_id, 0)
        self.assertEqual(out.event_type, "heal")
        self.assertEqual(out.state.agent(0).role, Role.HUMAN)
        self.assertEqual(out.state.agent(1).pos, (1, 1))
        self.assertEqual(out.state.agent(1).cooldown, 3)
        self.assertEqual(out.state.heals, 1)

    def test_stay_never_heals(self) -> None:
        """STAY never heals even with an adjacent zombie and cooldown 0."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 2, 1),
                agent(1, Role.HEALER, 1, 1, cooldown=0),
            ],
            current_index=1,
        )
        out = apply_action(state, 1, Action.STAY)
        self.assertIsNone(out.healed_id)
        self.assertEqual(out.state.agent(0).role, Role.ZOMBIE)
        # Healer stays next to zombie and gets infected (chain / adjacency).
        self.assertEqual(out.state.agent(1).role, Role.ZOMBIE)

    def test_healed_agent_can_be_reinfected_immediately(self) -> None:
        """A heal next to another zombie can be undone by chain infection in the same action."""
        # Z0 next to healer direction; Z2 also next to Z0's cell so healed agent is re-infected.
        # Layout: healer at (1,2), Z0 at (2,2), Z2 at (3,2). Heal Z0 -> human, then Z2 infects it.
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 2, 2),
                agent(1, Role.HEALER, 1, 2, cooldown=0),
                agent(2, Role.ZOMBIE, 3, 2),
            ],
            current_index=1,
            heal_cooldown=3,
        )
        out = apply_action(state, 1, Action.RIGHT)
        self.assertEqual(out.healed_id, 0)
        self.assertEqual(out.state.heals, 1)
        self.assertEqual(out.state.agent(0).role, Role.ZOMBIE)
        self.assertIn(0, out.newly_infected)
        self.assertEqual(out.event_type, "heal")

    def test_infected_healer_becomes_zombie(self) -> None:
        """An infected healer becomes a zombie and loses cooldown."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HEALER, 2, 1, cooldown=2),
            ],
        )
        out = apply_action(state, 0, Action.STAY)
        self.assertEqual(out.state.agent(1).role, Role.ZOMBIE)
        self.assertEqual(out.state.agent(1).cooldown, 0)

    def _cooldown_schedule(self, heal_cooldown: int) -> None:
        """Heal at T, then verify the next successful heal is at T+heal_cooldown."""
        from dataclasses import replace

        # Extra far zombie (id 2) keeps the game non-terminal after a heal.
        lines = [
            "###########",
            "#.........#",
            "#.........#",
            "###########",
        ]
        state = make_state(
            lines,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HEALER, 2, 1, cooldown=0),
                agent(2, Role.ZOMBIE, 9, 2),
            ],
            current_index=1,
            heal_cooldown=heal_cooldown,
            max_rounds=100,
        )
        out = apply_action(state, 1, Action.LEFT)
        self.assertEqual(out.healed_id, 0)
        self.assertEqual(out.state.agent(1).cooldown, heal_cooldown)
        self.assertFalse(out.state.done)
        state = out.state

        # heal_cooldown-1 own turns: cooldown ticks down, heal is impossible.
        for _ in range(1, heal_cooldown):
            state = replace(
                state,
                acted=frozenset(),
                skipped=frozenset(),
                current_index=1,
                round_number=state.round_number + 1,
            )
            before = state.agent(1).cooldown
            out = apply_action(state, 1, Action.RIGHT)
            self.assertEqual(out.state.agent(1).cooldown, before - 1)
            self.assertIsNone(out.healed_id)
            state = out.state

        # Next own turn: cooldown becomes 0 and a heal succeeds again.
        healer = state.agent(1)
        state = replace(
            state.replace_agents(
                {
                    0: state.agent(0).with_updates(role=Role.ZOMBIE, x=healer.x - 1, y=healer.y),
                    1: healer,
                }
            ),
            acted=frozenset(),
            skipped=frozenset(),
            current_index=1,
            round_number=state.round_number + 1,
        )
        self.assertEqual(state.agent(1).cooldown, 1)
        out = apply_action(state, 1, Action.LEFT)
        self.assertEqual(out.healed_id, 0)
        self.assertEqual(out.state.agent(1).cooldown, heal_cooldown)

    def test_cooldown_1(self) -> None:
        """With heal_cooldown=1, a heal at T allows the next heal at T+1."""
        self._cooldown_schedule(1)

    def test_cooldown_3(self) -> None:
        """With heal_cooldown=3, a heal at T allows the next heal at T+3."""
        self._cooldown_schedule(3)

    def test_cooldown_5(self) -> None:
        """With heal_cooldown=5, a heal at T allows the next heal at T+5."""
        self._cooldown_schedule(5)

    def test_heal_while_on_cooldown_is_illegal_if_cell_occupied(self) -> None:
        """Facing a zombie while cooldown > 0 is an illegal move into an occupied cell."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 2, 1),
                agent(1, Role.HEALER, 1, 1, cooldown=2),
            ],
            current_index=1,
            heal_cooldown=3,
        )
        # Start cooldown 2 -> 1 after decrement; heal not allowed; move into zombie = illegal.
        out = apply_action(state, 1, Action.RIGHT)
        self.assertTrue(out.illegal)
        self.assertEqual(out.event_type, "illegal")
        self.assertEqual(out.action, Action.STAY)
        self.assertEqual(out.state.agent(1).pos, (1, 1))
        self.assertEqual(out.state.illegal_actions, 1)
        # Still adjacent, so healer gets infected.
        self.assertEqual(out.state.agent(1).role, Role.ZOMBIE)

    def test_illegal_wall_and_occupied(self) -> None:
        """Moving into a wall or occupied cell becomes STAY and counts illegal_action."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 2, 1),
            ],
        )
        wall = apply_action(state, 0, Action.UP)
        self.assertTrue(wall.illegal)
        self.assertEqual(wall.action, Action.STAY)
        self.assertEqual(wall.state.illegal_actions, 1)

        occ = apply_action(state, 0, Action.RIGHT)
        self.assertTrue(occ.illegal)
        self.assertEqual(occ.state.agent(0).pos, (1, 1))

    def test_apply_action_is_pure(self) -> None:
        """apply_action never mutates its input state."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 4, 4),
            ],
        )
        snapshot = copy.deepcopy(state)
        apply_action(state, 0, Action.RIGHT)
        self.assertEqual(state, snapshot)
        self.assertEqual(state.key(), snapshot.key())

    def test_legal_actions_include_stay_and_free_moves(self) -> None:
        """legal_actions always includes STAY and excludes blocked cells."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 2, 1),
            ],
        )
        actions = legal_actions(state, 0)
        self.assertIn(Action.STAY, actions)
        self.assertNotIn(Action.RIGHT, actions)  # occupied by human
        self.assertNotIn(Action.UP, actions)  # wall
        self.assertNotIn(Action.LEFT, actions)  # wall
        self.assertIn(Action.DOWN, actions)

    def test_infection_targets_helper(self) -> None:
        """infection_targets lists only adjacent human-team agents."""
        state = make_state(
            OPEN,
            [
                agent(0, Role.ZOMBIE, 2, 2),
                agent(1, Role.HUMAN, 2, 1),
                agent(2, Role.HEALER, 5, 5),
            ],
        )
        self.assertEqual(infection_targets(state), [1])


if __name__ == "__main__":
    unittest.main()

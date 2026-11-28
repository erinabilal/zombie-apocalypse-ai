"""Unit tests for evaluation, minimax, alpha-beta and expectimax."""

from __future__ import annotations

import unittest

from adversarial._common import AdversarialStats
from adversarial.alphabeta import alphabeta
from adversarial.evaluation import evaluate
from adversarial.expectimax import expectimax
from adversarial.minimax import minimax
from game.entities import Action, Role
from game.rules import apply_action, advance_turn
from helpers import agent, make_state


class TestEvaluation(unittest.TestCase):
    """Basic evaluation sanity checks."""

    def test_win_loss_scores(self) -> None:
        """Terminal wins and losses dominate the heuristic."""
        z_win = make_state(
            ["#####", "#...#", "#####"],
            [agent(0, Role.ZOMBIE, 1, 1)],
        ).with_terminal("zombies", "all_infected")
        h_win = make_state(
            ["#####", "#...#", "#####"],
            [agent(0, Role.HUMAN, 1, 1)],
        ).with_terminal("humans", "no_zombies")
        self.assertGreater(evaluate(z_win, Role.ZOMBIE), 9000)
        self.assertLess(evaluate(h_win, Role.ZOMBIE), -9000)
        self.assertGreater(evaluate(h_win, Role.HUMAN), 9000)


class TestMinimaxAlphaBeta(unittest.TestCase):
    """Alpha-beta matches minimax and expands no more nodes."""

    def test_alphabeta_equals_minimax_fewer_nodes(self) -> None:
        """Same value as minimax; nodes_expanded is less than or equal."""
        state = make_state(
            [
                "#######",
                "#.....#",
                "#.....#",
                "#.....#",
                "#######",
            ],
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 5, 3),
            ],
            max_rounds=20,
            heal_cooldown=3,
        )
        mm_stats = AdversarialStats()
        ab_stats = AdversarialStats()
        mm_val, mm_act = minimax(state, 2, Role.ZOMBIE, 0, relevance_radius=10, stats=mm_stats)
        ab_val, ab_act = alphabeta(state, 2, Role.ZOMBIE, 0, relevance_radius=10, stats=ab_stats)
        self.assertAlmostEqual(mm_val, ab_val, places=6)
        self.assertEqual(mm_act, ab_act)
        self.assertLessEqual(ab_stats.nodes_expanded, mm_stats.nodes_expanded)


class TestExpectimax(unittest.TestCase):
    """Expectimax prefers escaping a corner against random opponents."""

    def test_expectimax_avoids_corner(self) -> None:
        """A human next to a dead-end prefers the escape action over stepping deeper in."""
        # Layout: human at (1,1) with a dead-end to the left corridor cell... 
        # Map with a corner pocket at (1,1) and escape to the right.
        lines = [
            "#####",
            "#H..#",
            "###.#",
            "#Z..#",
            "#####",
        ]
        # Build without spawn markers: place manually.
        lines = [
            "#####",
            "#...#",
            "###.#",
            "#...#",
            "#####",
        ]
        state = make_state(
            lines,
            [
                agent(0, Role.ZOMBIE, 1, 3),
                agent(1, Role.HUMAN, 1, 1),
            ],
            current_index=1,
            max_rounds=10,
        )
        # Human to move: LEFT is wall, UP wall, DOWN wall (###), RIGHT opens to (2,1).
        # STAY stays cornered. Expectimax should prefer RIGHT.
        stats = AdversarialStats()
        value, action = expectimax(
            state,
            depth=2,
            perspective=Role.HUMAN,
            viewer_id=1,
            relevance_radius=10,
            opponent_model="random",
            stats=stats,
        )
        self.assertEqual(action, Action.RIGHT)
        self.assertIsInstance(value, float)


class TestAdversarialPly(unittest.TestCase):
    """Search uses real apply_action / advance_turn."""

    def test_depth_one_returns_legal_action(self) -> None:
        """Depth-1 minimax returns a legal action for the current agent."""
        state = make_state(
            [
                "#####",
                "#...#",
                "#...#",
                "#####",
            ],
            [
                agent(0, Role.ZOMBIE, 1, 1),
                agent(1, Role.HUMAN, 3, 2),
            ],
        )
        _, action = minimax(state, 1, Role.ZOMBIE, 0, relevance_radius=6)
        self.assertIsNotNone(action)
        from game.rules import legal_actions

        self.assertIn(action, legal_actions(state, 0))

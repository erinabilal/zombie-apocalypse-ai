"""make_agent(name, id, role, config, rng): builds an agent from its name."""

from __future__ import annotations

import random

from agents.adversarial_agent import AdversarialAgent
from agents.base_agent import BaseAgent
from agents.random_agent import RandomAgent
from agents.rule_based_agent import RuleBasedAgent
from agents.search_agent import SearchAgent
from config import GameConfig
from game.entities import Role

_SEARCH_NAMES = frozenset({"bfs", "dfs", "ucs", "greedy", "astar"})
_ADV_NAMES = frozenset({"minimax", "alphabeta", "expectimax"})
_IMPLEMENTED = frozenset({"random", "rulebased"}) | _SEARCH_NAMES | _ADV_NAMES


def make_agent(
    name: str,
    agent_id: int,
    role: Role,
    config: GameConfig,
    rng: random.Random,
) -> BaseAgent:
    """Build an agent by name; unimplemented names raise a clear ValueError."""
    key = name.lower().strip()
    if key == "random":
        return RandomAgent(agent_id, rng)
    if key == "rulebased":
        return RuleBasedAgent(agent_id, rng)
    if key in _SEARCH_NAMES:
        return SearchAgent(
            agent_id,
            key,
            rng,
            heuristic=config.heuristic,
            use_belief_tracker=config.use_belief_tracker,
            hidden_roles=config.hidden_roles,
        )
    if key in _ADV_NAMES:
        return AdversarialAgent(
            agent_id,
            key,
            rng,
            search_depth=config.search_depth,
            move_time_limit=config.move_time_limit,
            node_budget=config.node_budget,
            relevance_radius=config.relevance_radius,
            opponent_model=config.opponent_model,
            heal_cooldown=config.heal_cooldown,
        )
    if key in {"manual", "qlearning"}:
        raise ValueError(
            f"agent {name!r} is not implemented yet "
            f"(supported: random, rulebased, search, minimax, alphabeta, expectimax)"
        )
    raise ValueError(f"unknown agent name {name!r}")

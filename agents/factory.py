"""make_agent(name, id, role, config, rng): builds an agent from its name."""

from __future__ import annotations

import random

from agents.adversarial_agent import AdversarialAgent
from agents.base_agent import BaseAgent
from agents.manual_agent import ManualAgent
from agents.random_agent import RandomAgent
from agents.rl_agent import RLAgent
from agents.rule_based_agent import RuleBasedAgent
from agents.search_agent import SearchAgent
from config import GameConfig
from game.entities import Role

_SEARCH_NAMES = frozenset({"bfs", "dfs", "ucs", "greedy", "astar"})
_ADV_NAMES = frozenset({"minimax", "alphabeta", "expectimax"})
_IMPLEMENTED = (
    frozenset({"random", "rulebased", "manual", "qlearning"}) | _SEARCH_NAMES | _ADV_NAMES
)


def make_agent(
    name: str,
    agent_id: int,
    role: Role,
    config: GameConfig,
    rng: random.Random,
    *,
    map_name: str = "small",
) -> BaseAgent:
    """Build an agent by name; unknown names raise ValueError."""
    key = name.lower().strip()
    if key == "manual":
        return ManualAgent(agent_id)
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
    if key == "qlearning":
        return RLAgent(agent_id, role, rng, map_name=map_name)
    raise ValueError(f"unknown agent name {name!r}")

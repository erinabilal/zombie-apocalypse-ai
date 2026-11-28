"""ZombieEnv: reset/step/legal_actions for one learner while others follow fixed policies."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from config import GameConfig
from game.engine import Engine, private_rng
from game.entities import Action, Role
from game.visibility import Observation

# Neighbor cell codes for the discrete state.
_FREE = 0
_WALL = 1
_OCCUPIED = 2

StateKey = tuple[Any, ...]


def encode_state(obs: Observation) -> StateKey:
    """
    Discretize an observation into a hashable tabular state.

    Features: own cell, clipped (dx,dy) to nearest visible enemy (or None),
    four neighbor flags, cooldown bucket, time-remaining bucket.
    """
    enemy = _nearest_enemy(obs)
    if enemy is None:
        rel: tuple[Any, ...] = (None, None)
    else:
        dx = max(-4, min(4, enemy[0] - obs.self_x))
        dy = max(-4, min(4, enemy[1] - obs.self_y))
        rel = (dx, dy)

    neighbors = tuple(
        _neighbor_flag(obs, dx, dy) for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
    )
    cd = obs.self_cooldown
    if cd <= 0:
        cd_bucket = 0
    elif cd <= 2:
        cd_bucket = 1
    else:
        cd_bucket = 2

    total = max(1, obs.round_number + obs.rounds_left - 1)
    frac = obs.rounds_left / total
    if frac > 0.66:
        time_bucket = 2
    elif frac > 0.33:
        time_bucket = 1
    else:
        time_bucket = 0

    return (
        obs.self_x,
        obs.self_y,
        rel[0],
        rel[1],
        neighbors[0],
        neighbors[1],
        neighbors[2],
        neighbors[3],
        cd_bucket,
        time_bucket,
        obs.self_role.value,
    )


def _nearest_enemy(obs: Observation) -> tuple[int, int] | None:
    """Nearest visible opponent cell for the learner's role."""
    best: tuple[int, int] | None = None
    best_d = 10**9
    for other in obs.visible_agents:
        if other.id == obs.self_id:
            continue
        if obs.self_role == Role.ZOMBIE:
            # Prefer human-team; unknown roles count as prey under hidden roles.
            if other.role == Role.ZOMBIE:
                continue
        else:
            if other.role is not None and other.role != Role.ZOMBIE:
                continue
        d = abs(other.x - obs.self_x) + abs(other.y - obs.self_y)
        if d < best_d:
            best_d = d
            best = (other.x, other.y)
    return best


def _neighbor_flag(obs: Observation, dx: int, dy: int) -> int:
    """Classify the orthogonal neighbor cell."""
    x, y = obs.self_x + dx, obs.self_y + dy
    if not obs.grid.in_bounds(x, y) or obs.grid.is_wall(x, y):
        return _WALL
    for other in obs.visible_agents:
        if other.x == x and other.y == y:
            return _OCCUPIED
    # Occupied by self is impossible for a neighbor; treat unseen as free.
    return _FREE


def compute_reward(
    config: GameConfig,
    role: Role,
    *,
    infections: int,
    heals: int,
    infected_self: bool,
    survived_round: bool,
    winner: str | None,
) -> float:
    """Role-specific reward using GameConfig reward_* constants."""
    r = 0.0
    if role == Role.ZOMBIE:
        r += config.reward_zombie_infection * infections
        r += config.reward_zombie_step
        if winner == "zombies":
            r += config.reward_zombie_win
    elif role == Role.HEALER:
        r += config.reward_healer_heal * heals
        if infected_self:
            r += config.reward_healer_infected
        if winner == "humans":
            r += config.reward_healer_win
    else:
        if survived_round:
            r += config.reward_human_survive_round
        if infected_self:
            r += config.reward_human_infected
        if winner == "humans":
            r += config.reward_human_win
    return r


class ZombieEnv:
    """
    Single-learner MDP wrapper around Engine.

    Other agents use fixed policies from GameConfig (default rulebased).
    """

    def __init__(
        self,
        config: GameConfig,
        *,
        learner_role: Role = Role.HUMAN,
        opponent_ai: str = "rulebased",
        map_name: str = "small",
    ) -> None:
        """Create an env; call reset() before step()."""
        self.base_config = config
        self.learner_role = learner_role
        self.opponent_ai = opponent_ai
        self.map_name = map_name
        self.engine: Engine | None = None
        self.learner_id: int | None = None
        self._episode = 0

    def reset(self, seed: int | None = None) -> StateKey:
        """Start a new episode; return the learner's initial state key."""
        seed = self.base_config.seed if seed is None else int(seed)
        # Assign AI names so the learner slot is unused by controllers.
        zombie_ai = self.opponent_ai
        human_ai = self.opponent_ai
        healer_ai = self.opponent_ai
        if self.learner_role == Role.ZOMBIE:
            zombie_ai = "random"  # placeholder; overridden by env actions
        elif self.learner_role == Role.HEALER:
            healer_ai = "random"
        else:
            human_ai = "random"

        cfg = replace(
            self.base_config,
            seed=seed,
            zombie_ai=zombie_ai,
            human_ai=human_ai,
            healer_ai=healer_ai,
        )
        self.engine = Engine(cfg)
        self.engine.reset()
        assert self.engine.state is not None

        # Pick the first agent matching the learner role.
        self.learner_id = None
        for agent in self.engine.state.agents:
            if agent.role == self.learner_role:
                self.learner_id = agent.id
                break
        if self.learner_id is None:
            raise RuntimeError(f"no agent with role {self.learner_role}")

        # Lazy import avoids circular dependency with agents.factory / RLAgent.
        from agents.factory import make_agent

        controllers = {}
        for agent in self.engine.state.agents:
            if agent.id == self.learner_id:
                continue
            controllers[agent.id] = make_agent(
                self.opponent_ai,
                agent.id,
                agent.role,
                cfg,
                private_rng(seed, agent.id),
            )
        self.engine.controllers = controllers
        self._episode += 1

        # Advance until the learner to act (or terminal).
        self._play_others()
        return self.state_key()

    def state_key(self) -> StateKey:
        """Current discrete state for the learner."""
        obs = self._obs()
        return encode_state(obs)

    def legal_actions(self) -> tuple[Action, ...]:
        """Legal actions for the learner now."""
        return tuple(self._obs().legal_actions)

    def step(self, action: Action) -> tuple[StateKey, float, bool, dict[str, Any]]:
        """Apply the learner action, simulate others, return (s', r, done, info)."""
        if self.engine is None or self.learner_id is None:
            raise RuntimeError("call reset() before step()")
        assert self.engine.state is not None
        if self.engine.state.done:
            raise RuntimeError("episode already finished")

        current = self.engine.state.current_agent()
        if current is None or current.id != self.learner_id:
            raise RuntimeError("not the learner's turn")

        before_round = self.engine.state.round_number
        before_role = current.role
        infections_before = self.engine.state.infections
        heals_before = self.engine.state.heals

        event = self.engine.step(action)

        infections = self.engine.state.infections - infections_before
        heals = 0
        if event.healed_id is not None:
            heals = self.engine.state.heals - heals_before

        # Did the learner get infected on this action's wave?
        infected_self = self.learner_id in event.newly_infected
        # Or converted later while others moved — checked after _play_others.

        self._play_others()
        assert self.engine.state is not None

        try:
            learner_now = self.engine.state.agent(self.learner_id)
        except KeyError:
            learner_now = None
        if (
            learner_now is not None
            and before_role.is_human_team()
            and learner_now.role == Role.ZOMBIE
        ):
            infected_self = True

        survived_round = False
        if (
            not infected_self
            and before_role.is_human_team()
            and self.engine.state.round_number > before_round
            and learner_now is not None
            and learner_now.role.is_human_team()
        ):
            survived_round = True

        winner = self.engine.state.winner if self.engine.state.done else None
        reward = compute_reward(
            self.engine.config,
            before_role,
            infections=infections if before_role == Role.ZOMBIE else 0,
            heals=heals if before_role == Role.HEALER else 0,
            infected_self=infected_self and before_role.is_human_team(),
            survived_round=survived_round,
            winner=winner,
        )

        done = bool(self.engine.state.done)
        if (
            self.learner_role.is_human_team()
            and learner_now is not None
            and learner_now.role == Role.ZOMBIE
        ):
            done = True

        info = {
            "winner": winner,
            "infected_self": infected_self,
            "infections": infections,
            "heals": heals,
        }
        if done:
            next_state = encode_state(self._obs()) if learner_now is not None else self.state_key()
        else:
            next_state = self.state_key()
        return next_state, float(reward), done, info

    def _obs(self) -> Observation:
        assert self.engine is not None and self.learner_id is not None
        return self.engine.observation_for(self.learner_id)

    def _play_others(self) -> None:
        """Step non-learner agents until the learner acts or the game ends."""
        assert self.engine is not None and self.learner_id is not None
        while self.engine.state is not None and not self.engine.state.done:
            current = self.engine.state.current_agent()
            if current is None:
                break
            if current.id == self.learner_id:
                # Human/healer learner who was infected: stop.
                if (
                    self.learner_role.is_human_team()
                    and current.role == Role.ZOMBIE
                ):
                    break
                break
            self.engine.step()

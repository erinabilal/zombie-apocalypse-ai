"""Engine: reset, step, play_round, run and the history of ActionEvents."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Protocol

from config import GameConfig
from game.entities import Action, AgentState, Role
from game.grid import Grid
from game.rules import ActionOutcome, advance_turn, apply_action, legal_actions
from game.state import GameState
from game.visibility import Observation, observe


class Controller(Protocol):
    """Anything the engine can ask for an action (avoids importing agents/)."""

    def get_action(self, obs: Observation) -> Action:
        """Choose an action from an observation."""


@dataclass(frozen=True)
class ActionEvent:
    """One recorded agent action and its effects."""

    agent_id: int
    action: Action
    event_type: str
    newly_infected: tuple[int, ...]
    healed_id: int | None
    illegal: bool
    round_number: int
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GameResult:
    """Final outcome of a finished game."""

    winner: str
    reason: str
    rounds_played: int
    zombies: int
    humans: int
    healers: int
    infections: int
    heals: int
    illegal_actions: int


def private_rng(seed: int, agent_id: int) -> random.Random:
    """Derive a private RNG for one agent from the game seed and its id."""
    return random.Random(seed * 1_000_003 + agent_id)


def spawn_agents(config: GameConfig, grid: Grid, rng: random.Random) -> tuple[AgentState, ...]:
    """Place zombies, humans and healers using markers first, then seeded random placement."""
    markers = dict(grid.spawn_markers)
    z_marks = [pos for pos, ch in markers.items() if ch == "Z"]
    h_marks = [pos for pos, ch in markers.items() if ch == "H"]
    d_marks = [pos for pos, ch in markers.items() if ch == "D"]

    occupied: set[tuple[int, int]] = set()
    agents: list[AgentState] = []
    next_id = 0

    def take_marked(positions: list[tuple[int, int]], count: int) -> list[tuple[int, int]]:
        chosen = positions[:count]
        for pos in chosen:
            occupied.add(pos)
        return chosen

    zombie_positions = take_marked(z_marks, config.n_zombies)
    human_positions = take_marked(h_marks, config.n_humans)
    healer_positions = take_marked(d_marks, config.n_healers)

    floors = grid.floor_cells()

    def place_random(n: int) -> list[tuple[int, int]]:
        placed: list[tuple[int, int]] = []
        free = [c for c in floors if c not in occupied]
        if len(free) < n:
            raise ValueError(f"not enough free cells to place {n} agents")
        picks = rng.sample(free, n)
        for pos in picks:
            occupied.add(pos)
            placed.append(pos)
        return placed

    need_z = config.n_zombies - len(zombie_positions)
    need_h = config.n_humans - len(human_positions)
    need_d = config.n_healers - len(healer_positions)
    if need_z > 0:
        zombie_positions.extend(place_random(need_z))
    if need_d > 0:
        healer_positions.extend(place_random(need_d))

    # Humans: enforce min_spawn_distance (path) from all zombies; relax by one up to 200 tries.
    if need_h > 0:
        human_positions.extend(
            _place_humans_with_distance(
                grid, rng, floors, occupied, zombie_positions, need_h, config.min_spawn_distance
            )
        )

    for pos in zombie_positions:
        agents.append(AgentState(id=next_id, role=Role.ZOMBIE, x=pos[0], y=pos[1]))
        next_id += 1
    for pos in human_positions:
        agents.append(AgentState(id=next_id, role=Role.HUMAN, x=pos[0], y=pos[1]))
        next_id += 1
    for pos in healer_positions:
        agents.append(AgentState(id=next_id, role=Role.HEALER, x=pos[0], y=pos[1]))
        next_id += 1

    return tuple(sorted(agents, key=lambda a: a.id))


def _place_humans_with_distance(
    grid: Grid,
    rng: random.Random,
    floors: list[tuple[int, int]],
    occupied: set[tuple[int, int]],
    zombie_positions: list[tuple[int, int]],
    n: int,
    min_distance: int,
) -> list[tuple[int, int]]:
    """Place n humans at least min_distance path steps from every zombie, relaxing on failure."""
    required = min_distance
    for _attempt in range(200):
        free = [c for c in floors if c not in occupied]
        if len(free) < n:
            break
        candidates = []
        for cell in free:
            if all(
                (d := grid.bfs_distance(cell, z)) is not None and d >= required
                for z in zombie_positions
            ):
                candidates.append(cell)
        if len(candidates) >= n:
            picks = rng.sample(candidates, n)
            for pos in picks:
                occupied.add(pos)
            return picks
        # Relax by one and retry with a reshuffle of free cells.
        required = max(0, required - 1)
        rng.shuffle(free)
    # Last resort: any free cells.
    free = [c for c in floors if c not in occupied]
    if len(free) < n:
        raise ValueError(f"cannot place {n} humans on the map")
    picks = rng.sample(free, n)
    for pos in picks:
        occupied.add(pos)
    return picks


def render_grid(state: GameState) -> str:
    """Return a text rendering of the grid with agents overlaid."""
    marks = {
        Role.ZOMBIE: "Z",
        Role.HUMAN: "H",
        Role.HEALER: "+",
    }
    overlay: dict[tuple[int, int], str] = {}
    for agent in state.agents:
        overlay[agent.pos] = marks[agent.role]
    lines: list[str] = []
    for y in range(state.grid.height):
        row: list[str] = []
        for x in range(state.grid.width):
            if (x, y) in overlay:
                row.append(overlay[(x, y)])
            elif state.grid.is_wall(x, y):
                row.append("#")
            else:
                cost = state.grid.cost(x, y)
                row.append("." if cost == 1 else str(cost))
        lines.append("".join(row))
    return "\n".join(lines)


class Engine:
    """Turn-based game runner. Controllers are injected; game/ never imports agents/."""

    def __init__(
        self,
        config: GameConfig,
        controllers: dict[int, Controller] | None = None,
    ) -> None:
        """Store config; call reset() before playing. Controllers may be set later."""
        self.config = config
        self.controllers: dict[int, Controller] = controllers or {}
        self.grid = Grid.from_lines(config.map_text)
        self.state: GameState | None = None
        self.history: list[ActionEvent] = []
        self.result: GameResult | None = None
        self._master_rng = random.Random(config.seed)

    def reset(self, controllers: dict[int, Controller] | None = None) -> GameState:
        """Spawn agents and return the initial state."""
        if controllers is not None:
            self.controllers = controllers
        self._master_rng = random.Random(self.config.seed)
        agents = spawn_agents(self.config, self.grid, self._master_rng)
        self.state = GameState(
            grid=self.grid,
            agents=agents,
            round_number=1,
            current_index=0,
            skipped=frozenset(),
            acted=frozenset(),
            infections=0,
            heals=0,
            illegal_actions=0,
            max_rounds=self.config.max_rounds,
            heal_cooldown=self.config.heal_cooldown,
        )
        self.history = []
        self.result = None
        return self.state

    def observation_for(self, agent_id: int) -> Observation:
        """Build the observation the given agent would see right now."""
        if self.state is None:
            raise RuntimeError("call reset() before observation_for()")
        return observe(
            self.state,
            agent_id,
            self.config.vision_radius,
            self.config.hidden_roles,
            self.config.identify_radius,
        )

    def step(self, action: Action | None = None) -> ActionEvent:
        """Advance exactly one agent action; optional manual action overrides the controller."""
        if self.state is None:
            raise RuntimeError("call reset() before step()")
        if self.state.done:
            raise RuntimeError("game is already finished")

        agent = self.state.current_agent()
        if agent is None:
            raise RuntimeError("no current agent")

        stats: dict[str, Any] = {}
        if action is None:
            controller = self.controllers.get(agent.id)
            if controller is None:
                raise RuntimeError(f"no controller for agent {agent.id}")
            obs = self.observation_for(agent.id)
            chosen = controller.get_action(obs)
            # Pull stats if the controller exposes a stats list.
            stats_list = getattr(controller, "stats", None)
            if isinstance(stats_list, list) and stats_list:
                last = stats_list[-1]
                if isinstance(last, dict):
                    stats = dict(last)
        else:
            chosen = action

        before = self.state
        outcome: ActionOutcome = apply_action(before, agent.id, chosen)
        self.state = advance_turn(outcome.state)
        event = ActionEvent(
            agent_id=agent.id,
            action=outcome.action,
            event_type=outcome.event_type,
            newly_infected=outcome.newly_infected,
            healed_id=outcome.healed_id,
            illegal=outcome.illegal,
            round_number=before.round_number,
            stats=stats,
        )
        self.history.append(event)
        if self.state.done:
            self.result = self._make_result(self.state)
        return event

    def play_round(self) -> list[ActionEvent]:
        """Play until the current round ends or the game finishes."""
        if self.state is None:
            raise RuntimeError("call reset() before play_round()")
        start_round = self.state.round_number
        events: list[ActionEvent] = []
        while not self.state.done and self.state.round_number == start_round:
            # Detect round end: after step, round_number increases or done.
            before_round = self.state.round_number
            before_acted = len(self.state.acted)
            event = self.step()
            events.append(event)
            if self.state.done:
                break
            if self.state.round_number != before_round:
                break
            # Safety: if nothing progressed, stop.
            if len(self.state.acted) == before_acted and self.state.round_number == before_round:
                break
        return events

    def run(self) -> GameResult:
        """Play until the game ends and return the result."""
        if self.state is None:
            self.reset()
        assert self.state is not None
        while not self.state.done:
            self.step()
        assert self.result is not None
        return self.result

    def _make_result(self, state: GameState) -> GameResult:
        """Build a GameResult from a terminal state."""
        assert state.winner is not None and state.reason is not None
        return GameResult(
            winner=state.winner,
            reason=state.reason,
            rounds_played=state.round_number,
            zombies=state.count(Role.ZOMBIE),
            humans=state.count(Role.HUMAN),
            healers=state.count(Role.HEALER),
            infections=state.infections,
            heals=state.heals,
            illegal_actions=state.illegal_actions,
        )

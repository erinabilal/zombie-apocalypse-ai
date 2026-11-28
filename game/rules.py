"""Game rules: legal_actions, pure apply_action, infection_targets, advance_turn, is_terminal, winner, step_cost."""

from __future__ import annotations

from dataclasses import dataclass, replace

from game.entities import ACTION_DELTAS, MOVE_ACTIONS, Action, AgentState, Role
from game.grid import Grid
from game.state import GameState


@dataclass(frozen=True)
class ActionOutcome:
    """Result of applying one action without mutating the input state."""

    state: GameState
    action: Action
    event_type: str
    newly_infected: tuple[int, ...]
    healed_id: int | None
    illegal: bool


def legal_actions(state: GameState, agent_id: int) -> list[Action]:
    """Return legal actions: STAY, free moves, and (for a ready healer) heal directions."""
    agent = state.agent(agent_id)
    occupied = state.occupied_cells()
    actions: list[Action] = [Action.STAY]
    for action in MOVE_ACTIONS:
        dx, dy = ACTION_DELTAS[action]
        nx, ny = agent.x + dx, agent.y + dy
        if state.grid.is_floor(nx, ny) and (nx, ny) not in occupied:
            actions.append(action)
    # Heal directions: after the turn-start cooldown tick, a ready healer may face an adjacent zombie.
    if agent.role == Role.HEALER and max(0, agent.cooldown - 1) == 0:
        for action in MOVE_ACTIONS:
            if action in actions:
                continue
            dx, dy = ACTION_DELTAS[action]
            nx, ny = agent.x + dx, agent.y + dy
            target = _agent_at(state, nx, ny)
            if target is not None and target.role == Role.ZOMBIE:
                actions.append(action)
    return actions


def step_cost(grid: Grid, x: int, y: int) -> int:
    """Return the terrain cost of entering cell (x, y)."""
    return grid.cost(x, y)


def infection_targets(state: GameState) -> list[int]:
    """Return human-team ids orthogonally adjacent to at least one zombie."""
    zombie_cells = {(a.x, a.y) for a in state.agents if a.role == Role.ZOMBIE}
    if not zombie_cells:
        return []
    targets: list[int] = []
    for agent in state.agents:
        if not agent.role.is_human_team():
            continue
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if (agent.x + dx, agent.y + dy) in zombie_cells:
                targets.append(agent.id)
                break
    return targets


def _apply_infections(state: GameState) -> tuple[GameState, tuple[int, ...]]:
    """Infect in waves until no human-team agent is adjacent to a zombie."""
    infected: list[int] = []
    current = state
    while True:
        targets = infection_targets(current)
        if not targets:
            break
        updates: dict[int, AgentState] = {}
        skip = set(current.skipped)
        for agent_id in targets:
            agent = current.agent(agent_id)
            updates[agent_id] = agent.with_updates(role=Role.ZOMBIE, cooldown=0)
            infected.append(agent_id)
            if agent_id not in current.acted:
                skip.add(agent_id)
        current = current.replace_agents(updates)
        current = replace(
            current,
            infections=current.infections + len(targets),
            skipped=frozenset(skip),
        )
    return current, tuple(infected)


def is_terminal(state: GameState) -> bool:
    """Return True if the game has ended or an early win condition currently holds."""
    if state.done:
        return True
    if state.count_human_team() == 0:
        return True
    if state.count_zombies() == 0:
        return True
    return False


def winner(state: GameState) -> tuple[str, str] | None:
    """Return (winner, reason) for early wins, or the stored result if already done."""
    if state.done and state.winner is not None and state.reason is not None:
        return state.winner, state.reason
    if state.count_human_team() == 0:
        return "zombies", "all_infected"
    if state.count_zombies() == 0:
        return "humans", "no_zombies"
    return None


def check_terminal_after_action(state: GameState) -> GameState:
    """Apply early win checks after an action; time_limit is handled in advance_turn."""
    result = winner(state)
    if result is None:
        return state
    side, reason = result
    return state.with_terminal(side, reason)


def _time_limit_result(state: GameState) -> GameState:
    """Zombies win on time only if zombies > humans; a tie is a human win."""
    if state.count_zombies() > state.count_human_team():
        return state.with_terminal("zombies", "time_limit")
    return state.with_terminal("humans", "time_limit")


def _resolve_destination(
    state: GameState, agent: AgentState, action: Action
) -> tuple[int, int, Action, bool]:
    """Return (x, y, effective_action, illegal) for an attempted move or stay."""
    if action == Action.STAY:
        return agent.x, agent.y, Action.STAY, False
    dx, dy = ACTION_DELTAS[action]
    nx, ny = agent.x + dx, agent.y + dy
    occupied = state.occupied_cells()
    if not state.grid.is_floor(nx, ny) or (nx, ny) in occupied:
        return agent.x, agent.y, Action.STAY, True
    return nx, ny, action, False


def _agent_at(state: GameState, x: int, y: int) -> AgentState | None:
    """Return the agent on (x, y), if any."""
    for agent in state.agents:
        if agent.x == x and agent.y == y:
            return agent
    return None


def _event_type(
    illegal: bool,
    healed_id: int | None,
    newly_infected: tuple[int, ...],
    effective: Action,
) -> str:
    """Pick one event type: illegal, then heal, then infect, then move or stay."""
    if illegal:
        return "illegal"
    if healed_id is not None:
        return "heal"
    if newly_infected:
        return "infect"
    if effective == Action.STAY:
        return "stay"
    return "move"


def apply_action(state: GameState, agent_id: int, action: Action) -> ActionOutcome:
    """Apply one agent action purely (never mutates state); used by the engine and search."""
    if state.done:
        raise ValueError("cannot apply_action on a terminal state")
    agent = state.agent(agent_id)
    working = state
    cooldown = agent.cooldown
    if agent.role == Role.HEALER:
        cooldown = max(0, cooldown - 1)

    healed_id: int | None = None
    illegal = False
    effective = action

    if agent.role == Role.HEALER and action != Action.STAY and cooldown == 0:
        dx, dy = ACTION_DELTAS[action]
        tx, ty = agent.x + dx, agent.y + dy
        target = _agent_at(working, tx, ty)
        if target is not None and target.role == Role.ZOMBIE:
            healed = target.with_updates(role=Role.HUMAN, cooldown=0)
            healer = agent.with_updates(cooldown=working.heal_cooldown)
            skip = set(working.skipped)
            if healed.id not in working.acted:
                skip.add(healed.id)
            working = working.replace_agents({healer.id: healer, healed.id: healed})
            working = replace(working, heals=working.heals + 1, skipped=frozenset(skip))
            healed_id = healed.id
            effective = action
        else:
            new_x, new_y, effective, illegal = _resolve_destination(working, agent, action)
            working = working.replace_agent(
                agent.with_updates(x=new_x, y=new_y, cooldown=cooldown)
            )
    else:
        new_x, new_y, effective, illegal = _resolve_destination(working, agent, action)
        working = working.replace_agent(
            agent.with_updates(x=new_x, y=new_y, cooldown=cooldown)
        )

    if illegal:
        working = replace(working, illegal_actions=working.illegal_actions + 1)

    working = replace(working, acted=frozenset(set(working.acted) | {agent_id}))
    working, newly_infected = _apply_infections(working)
    working = check_terminal_after_action(working)

    return ActionOutcome(
        state=working,
        action=effective,
        event_type=_event_type(illegal, healed_id, newly_infected, effective),
        newly_infected=newly_infected,
        healed_id=healed_id,
        illegal=illegal,
    )


def advance_turn(state: GameState) -> GameState:
    """Move to the next agent that still owes an action this round, or start/end the next round."""
    if state.done:
        return state
    early = winner(state)
    if early is not None:
        side, reason = early
        return state.with_terminal(side, reason)

    current_id = state.agents[state.current_index].id
    later = [
        agent
        for agent in state.agents
        if agent.id > current_id
        and agent.id not in state.acted
        and agent.id not in state.skipped
    ]
    if later:
        return replace(state, current_index=state.agent_index(later[0].id))

    # Round finished: early wins first, then time limit, else next round.
    early = winner(state)
    if early is not None:
        side, reason = early
        return state.with_terminal(side, reason)
    if state.round_number >= state.max_rounds:
        return _time_limit_result(state)

    return replace(
        state,
        round_number=state.round_number + 1,
        skipped=frozenset(),
        acted=frozenset(),
        current_index=0,
    )

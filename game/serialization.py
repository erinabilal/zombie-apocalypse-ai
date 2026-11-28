"""Conversion of config, state and events to and from plain JSON-compatible dicts."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from config import GameConfig
from game.entities import Action, AgentState, Role
from game.engine import ActionEvent, GameResult
from game.grid import Grid
from game.state import GameState


def config_to_dict(config: GameConfig) -> dict[str, Any]:
    """Serialize GameConfig to a plain dict."""
    return {f.name: getattr(config, f.name) for f in fields(config)}


def config_from_dict(data: dict[str, Any]) -> GameConfig:
    """Deserialize GameConfig from a plain dict."""
    allowed = {f.name for f in fields(GameConfig)}
    kwargs = {k: v for k, v in data.items() if k in allowed}
    return GameConfig(**kwargs)


def agent_to_dict(agent: AgentState) -> dict[str, Any]:
    """Serialize one AgentState."""
    return {
        "id": agent.id,
        "role": agent.role.value,
        "x": agent.x,
        "y": agent.y,
        "cooldown": agent.cooldown,
    }


def agent_from_dict(data: dict[str, Any]) -> AgentState:
    """Deserialize one AgentState."""
    return AgentState(
        id=int(data["id"]),
        role=Role(data["role"]),
        x=int(data["x"]),
        y=int(data["y"]),
        cooldown=int(data.get("cooldown", 0)),
    )


def grid_to_dict(grid: Grid) -> dict[str, Any]:
    """Serialize a Grid (map text is enough to rebuild)."""
    return {
        "width": grid.width,
        "height": grid.height,
        "lines": grid.to_lines(),
    }


def grid_from_dict(data: dict[str, Any]) -> Grid:
    """Deserialize a Grid from lines."""
    return Grid.from_lines(data["lines"])


def state_to_dict(state: GameState) -> dict[str, Any]:
    """Serialize GameState to a plain dict."""
    return {
        "grid": grid_to_dict(state.grid),
        "agents": [agent_to_dict(a) for a in state.agents],
        "round_number": state.round_number,
        "current_index": state.current_index,
        "skipped": sorted(state.skipped),
        "acted": sorted(state.acted),
        "infections": state.infections,
        "heals": state.heals,
        "illegal_actions": state.illegal_actions,
        "max_rounds": state.max_rounds,
        "heal_cooldown": state.heal_cooldown,
        "done": state.done,
        "winner": state.winner,
        "reason": state.reason,
    }


def state_from_dict(data: dict[str, Any]) -> GameState:
    """Deserialize GameState from a plain dict."""
    agents = tuple(
        sorted((agent_from_dict(a) for a in data["agents"]), key=lambda a: a.id)
    )
    return GameState(
        grid=grid_from_dict(data["grid"]),
        agents=agents,
        round_number=int(data["round_number"]),
        current_index=int(data["current_index"]),
        skipped=frozenset(int(x) for x in data.get("skipped", [])),
        acted=frozenset(int(x) for x in data.get("acted", [])),
        infections=int(data["infections"]),
        heals=int(data["heals"]),
        illegal_actions=int(data["illegal_actions"]),
        max_rounds=int(data["max_rounds"]),
        heal_cooldown=int(data["heal_cooldown"]),
        done=bool(data.get("done", False)),
        winner=data.get("winner"),
        reason=data.get("reason"),
    )


def event_to_dict(event: ActionEvent) -> dict[str, Any]:
    """Serialize an ActionEvent."""
    return {
        "agent_id": event.agent_id,
        "action": event.action.name,
        "event_type": event.event_type,
        "newly_infected": list(event.newly_infected),
        "healed_id": event.healed_id,
        "illegal": event.illegal,
        "round_number": event.round_number,
        "stats": dict(event.stats),
    }


def event_from_dict(data: dict[str, Any]) -> ActionEvent:
    """Deserialize an ActionEvent."""
    action_raw = data["action"]
    action = Action[action_raw] if isinstance(action_raw, str) else Action(action_raw)
    return ActionEvent(
        agent_id=int(data["agent_id"]),
        action=action,
        event_type=str(data["event_type"]),
        newly_infected=tuple(int(x) for x in data.get("newly_infected", [])),
        healed_id=data.get("healed_id"),
        illegal=bool(data.get("illegal", False)),
        round_number=int(data["round_number"]),
        stats=dict(data.get("stats", {})),
    )


def result_to_dict(result: GameResult) -> dict[str, Any]:
    """Serialize a GameResult."""
    return {
        "winner": result.winner,
        "reason": result.reason,
        "rounds_played": result.rounds_played,
        "zombies": result.zombies,
        "humans": result.humans,
        "healers": result.healers,
        "infections": result.infections,
        "heals": result.heals,
        "illegal_actions": result.illegal_actions,
    }


def result_from_dict(data: dict[str, Any]) -> GameResult:
    """Deserialize a GameResult."""
    return GameResult(
        winner=str(data["winner"]),
        reason=str(data["reason"]),
        rounds_played=int(data["rounds_played"]),
        zombies=int(data["zombies"]),
        humans=int(data["humans"]),
        healers=int(data["healers"]),
        infections=int(data["infections"]),
        heals=int(data["heals"]),
        illegal_actions=int(data.get("illegal_actions", 0)),
    )

"""Browser bridge: plain functions taking/returning JSON-friendly dicts (single Engine)."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from agents.factory import make_agent
from config import AGENT_NAMES, HEURISTIC_NAMES, GameConfig, WEB_MAX_SEARCH_DEPTH
from game.engine import Engine, private_rng
from game.entities import Action, Role
from game.serialization import (
    config_from_dict,
    config_to_dict,
    event_to_dict,
    result_to_dict,
    state_to_dict,
)

# Populated by the worker (or tests) via set_maps / load_maps_json.
_MAPS: dict[str, str] = {}
_engine: Engine | None = None
_config: GameConfig | None = None
_agent_names: dict[int, str] = {}


def set_maps(maps: dict[str, str]) -> None:
    """Register map name -> map_text for list_options and new_game shortcuts."""
    global _MAPS
    _MAPS = dict(maps)


def load_maps_json(text: str) -> None:
    """Load maps from a maps.json string: {name: {lines: [...] } or name: text}."""
    data = json.loads(text)
    maps: dict[str, str] = {}
    for name, value in data.items():
        if isinstance(value, str):
            maps[name] = value
        elif isinstance(value, dict) and "text" in value:
            maps[name] = value["text"]
        elif isinstance(value, dict) and "lines" in value:
            maps[name] = "\n".join(value["lines"])
        else:
            raise ValueError(f"invalid map entry for {name!r}")
    set_maps(maps)


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a success payload."""
    return payload


def _err(message: str) -> dict[str, Any]:
    """Return an error payload instead of raising."""
    return {"error": message}


def _require_engine() -> Engine | dict[str, Any]:
    """Return the current engine or an error dict."""
    if _engine is None or _engine.state is None:
        return _err("no active game; call new_game first")
    return _engine


def _map_cells(engine: Engine) -> dict[str, Any]:
    """Build the map payload for the canvas renderer."""
    grid = engine.grid
    cells: list[list[Any]] = []
    for y in range(grid.height):
        row: list[Any] = []
        for x in range(grid.width):
            if grid.is_wall(x, y):
                row.append({"wall": True, "cost": 0})
            else:
                row.append({"wall": False, "cost": grid.cost(x, y)})
        cells.append(row)
    return {"width": grid.width, "height": grid.height, "cells": cells}


def _agents_meta(engine: Engine) -> list[dict[str, Any]]:
    """List agents with id, role and AI name."""
    assert engine.state is not None
    rows = []
    for agent in engine.state.agents:
        rows.append(
            {
                "id": agent.id,
                "role": agent.role.value,
                "ai": _agent_names.get(agent.id, "unknown"),
            }
        )
    return rows


def _build_controllers(config: GameConfig, engine: Engine) -> dict[int, Any]:
    """Create controllers for every spawned agent."""
    assert engine.state is not None
    controllers = {}
    names: dict[int, str] = {}
    for agent in engine.state.agents:
        if agent.role == Role.ZOMBIE:
            name = config.zombie_ai
        elif agent.role == Role.HEALER:
            name = config.healer_ai
        else:
            name = config.human_ai
        names[agent.id] = name
        controllers[agent.id] = make_agent(
            name, agent.id, agent.role, config, private_rng(config.seed, agent.id)
        )
    global _agent_names
    _agent_names = names
    return controllers


def _resolve_config(config_json: str | dict[str, Any]) -> GameConfig:
    """Parse config JSON/dict, resolve map name, and cap web search depth."""
    data = json.loads(config_json) if isinstance(config_json, str) else dict(config_json)
    if "map_text" not in data or not data.get("map_text"):
        map_name = data.pop("map", data.pop("map_name", "small"))
        if map_name not in _MAPS:
            raise ValueError(f"unknown map {map_name!r}; known: {', '.join(sorted(_MAPS)) or '(none)'}")
        data["map_text"] = _MAPS[map_name]
    else:
        data.pop("map", None)
        data.pop("map_name", None)
    if "search_depth" in data:
        data["search_depth"] = min(int(data["search_depth"]), WEB_MAX_SEARCH_DEPTH)
    else:
        data["search_depth"] = min(2, WEB_MAX_SEARCH_DEPTH)
    # Keep adversarial moves snappy in the browser.
    if "move_time_limit" not in data:
        data["move_time_limit"] = 0.25
    return config_from_dict(data)


def new_game(config_json: str | dict[str, Any]) -> dict[str, Any]:
    """Start a new game; returns state, config, agents and map cells."""
    global _engine, _config
    try:
        config = _resolve_config(config_json)
        engine = Engine(config)
        engine.reset()
        engine.controllers = _build_controllers(config, engine)
        _engine = engine
        _config = config
        assert engine.state is not None
        return _ok(
            {
                "state": state_to_dict(engine.state),
                "config": config_to_dict(config),
                "agents": _agents_meta(engine),
                "map": _map_cells(engine),
            }
        )
    except Exception as exc:  # noqa: BLE001 — bridge must not throw to JS
        return _err(str(exc))


def _step_result(engine: Engine, event: Any) -> dict[str, Any]:
    """Build the common step/play_round response fields for one event."""
    assert engine.state is not None
    result = result_to_dict(engine.result) if engine.result is not None else None
    return {
        "event": event_to_dict(event),
        "state": state_to_dict(engine.state),
        "done": engine.state.done,
        "result": result,
    }


def step() -> dict[str, Any]:
    """Advance exactly one agent action using its controller."""
    engine = _require_engine()
    if isinstance(engine, dict):
        return engine
    try:
        if engine.state is not None and engine.state.done:
            return _err("game is already finished")
        # If the current agent is manual, do not auto-step.
        assert engine.state is not None
        current = engine.state.current_agent()
        if current is not None and _agent_names.get(current.id) == "manual":
            return _err("manual agent waiting for submit_manual_action")
        event = engine.step()
        return _ok(_step_result(engine, event))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def play_round() -> dict[str, Any]:
    """Play until the current round ends or the game finishes (stops before manual)."""
    engine = _require_engine()
    if isinstance(engine, dict):
        return engine
    try:
        assert engine.state is not None
        if engine.state.done:
            return _err("game is already finished")
        start_round = engine.state.round_number
        events = []
        while not engine.state.done and engine.state.round_number == start_round:
            current = engine.state.current_agent()
            if current is not None and _agent_names.get(current.id) == "manual":
                break
            event = engine.step()
            events.append(event_to_dict(event))
            if engine.state.done:
                break
            if engine.state.round_number != start_round:
                break
        result = result_to_dict(engine.result) if engine.result is not None else None
        return _ok(
            {
                "events": events,
                "state": state_to_dict(engine.state),
                "done": engine.state.done,
                "result": result,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def submit_manual_action(action: str | int) -> dict[str, Any]:
    """Apply a manual action for the current agent (same shape as step)."""
    engine = _require_engine()
    if isinstance(engine, dict):
        return engine
    try:
        assert engine.state is not None
        if engine.state.done:
            return _err("game is already finished")
        if isinstance(action, int):
            chosen = Action(action)
        else:
            key = str(action).strip().upper()
            chosen = Action[key]
        event = engine.step(action=chosen)
        return _ok(_step_result(engine, event))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def get_observation(agent_id: int) -> dict[str, Any]:
    """Return visible cells and agents for the vision overlay."""
    engine = _require_engine()
    if isinstance(engine, dict):
        return engine
    try:
        obs = engine.observation_for(int(agent_id))
        return _ok(
            {
                "visible_cells": [[x, y] for x, y in sorted(obs.visible_cells)],
                "visible_agents": [
                    {
                        "id": a.id,
                        "x": a.x,
                        "y": a.y,
                        "role": None if a.role is None else a.role.value,
                    }
                    for a in obs.visible_agents
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def get_belief_map(agent_id: int) -> dict[str, Any]:
    """Return danger_map cells [[x,y,p], ...] for the selected agent's tracker."""
    engine = _require_engine()
    if isinstance(engine, dict):
        return engine
    try:
        controller = engine.controllers.get(int(agent_id))
        belief = getattr(controller, "belief", None)
        if belief is None:
            # Trigger an update if the agent supports belief but has not acted yet.
            if controller is not None and hasattr(controller, "use_belief_tracker"):
                obs = engine.observation_for(int(agent_id))
                if getattr(controller, "use_belief_tracker", False):
                    from agents.belief_tracker import BeliefTracker

                    if getattr(controller, "belief", None) is None:
                        controller.belief = BeliefTracker(
                            obs.grid,
                            int(agent_id),
                            hidden_roles=getattr(controller, "hidden_roles", False),
                        )
                    controller.belief.update(obs)
                    belief = controller.belief
        if belief is None:
            return _ok({"cells": []})
        danger = belief.danger_map()
        cells = [[x, y, p] for (x, y), p in danger.items() if p > 1e-6]
        cells.sort(key=lambda row: (-row[2], row[1], row[0]))
        return _ok({"cells": cells})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def run_compare(
    config_json: str | dict[str, Any],
    agent_names: list[str] | str,
    n_games: int,
) -> dict[str, Any]:
    """Run a small compare batch for one role's AI list (uses evaluation.compare_mode)."""
    try:
        from evaluation.compare_mode import compare_agents

        if isinstance(agent_names, str):
            names = [n.strip() for n in agent_names.split(",") if n.strip()]
        else:
            names = list(agent_names)
        n_games = int(n_games)
        if n_games < 1 or n_games > 30:
            return _err("n_games must be between 1 and 30 in the browser")
        raw = json.loads(config_json) if isinstance(config_json, str) else dict(config_json)
        compare_role = str(raw.pop("_compare_role", "zombie")).lower()
        base = _resolve_config(raw)
        base = replace(
            base,
            search_depth=min(base.search_depth, WEB_MAX_SEARCH_DEPTH),
            move_time_limit=min(float(base.move_time_limit), 0.5),
        )
        rows = compare_agents(base, names, n_games, role=compare_role)
        # Browser chart table expects a compact column set.
        compact = []
        for row in rows:
            compact.append(
                {
                    "agent": row["agent"],
                    "games": row["games"],
                    "win_rate": row["win_rate"],
                    "avg_rounds": row["avg_rounds"],
                    "avg_nodes_expanded": row["avg_nodes_expanded"],
                    "avg_time_per_move": row["avg_time_per_move"],
                    "compare_role": row.get("compare_role", compare_role),
                    "win_rate_lo": row.get("win_rate_lo"),
                    "win_rate_hi": row.get("win_rate_hi"),
                }
            )
        return _ok({"rows": compact})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def list_options() -> dict[str, Any]:
    """Return available maps, agents and heuristics for the UI."""
    return _ok(
        {
            "maps": sorted(_MAPS.keys()) if _MAPS else ["small", "medium", "large"],
            "agents": list(AGENT_NAMES),
            "heuristics": list(HEURISTIC_NAMES),
        }
    )


def load_models_json(text: str) -> dict[str, Any]:
    """
    Register Q-tables from a models index JSON string.

    Expected shapes:
      {"items":[{"role":"human","file":"...","data":{...QTable...}}]}
      or {"human": { ...QTable... }, "zombie": {...}}
    """
    try:
        from rl.q_learning import QTable, clear_registry, register_q_table

        clear_registry()
        data = json.loads(text) if isinstance(text, str) else dict(text)
        loaded = 0
        if "items" in data:
            for item in data["items"]:
                role = str(item.get("role", "")).lower()
                payload = item.get("data")
                if not role or not isinstance(payload, dict):
                    continue
                register_q_table(role, QTable.from_dict(payload))
                loaded += 1
        else:
            for role, payload in data.items():
                if isinstance(payload, dict) and "q" in payload:
                    register_q_table(str(role), QTable.from_dict(payload))
                    loaded += 1
        return _ok({"loaded": loaded})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def call(fn: str, args: list[Any] | None = None) -> dict[str, Any]:
    """Dispatch a worker message {fn, args} to the matching bridge function."""
    args = args or []
    table = {
        "new_game": new_game,
        "step": step,
        "play_round": play_round,
        "submit_manual_action": submit_manual_action,
        "get_observation": get_observation,
        "get_belief_map": get_belief_map,
        "run_compare": run_compare,
        "list_options": list_options,
        "load_maps_json": load_maps_json,
        "load_models_json": load_models_json,
        "set_maps": set_maps,
    }
    if fn not in table:
        return _err(f"unknown function {fn!r}")
    try:
        return table[fn](*args)
    except TypeError as exc:
        return _err(str(exc))

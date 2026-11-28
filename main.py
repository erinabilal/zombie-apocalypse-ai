"""Command-line entry point: headless runs, --compare and --desktop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agents.factory import make_agent
from config import AGENT_NAMES, GameConfig
from game.engine import Engine, GameResult, private_rng, render_grid


class CliError(Exception):
    """Invalid CLI usage; main() maps this to exit code 2."""


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the headless CLI."""
    parser = argparse.ArgumentParser(description="Zombie Apocalypse AI")
    parser.add_argument("--map", dest="map_path", default="maps/small.txt")
    parser.add_argument("--zombies", type=int, default=1)
    parser.add_argument("--humans", type=int, default=4)
    parser.add_argument("--healers", type=int, default=1)
    parser.add_argument("--rounds", type=int, default=60)
    parser.add_argument("--heal-cooldown", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--vision", type=int, default=None)
    parser.add_argument("--hidden-roles", action="store_true")
    parser.add_argument("--zombie-ai", default="rulebased")
    parser.add_argument("--human-ai", default="rulebased")
    parser.add_argument("--healer-ai", default="rulebased")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument(
        "--heuristic",
        default="manhattan",
        choices=["manhattan", "euclidean", "maze"],
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument(
        "--compare-role",
        default="zombie",
        choices=["zombie", "human", "healer"],
        help="Which role's AI list to vary in --compare mode",
    )
    parser.add_argument("--games", type=int, default=200)
    return parser


def _load_map_text(path: str) -> str:
    """Read map text from a file path relative to the project root or absolute."""
    map_path = Path(path)
    if not map_path.is_file():
        alt = Path(__file__).resolve().parent / path
        if alt.is_file():
            map_path = alt
        else:
            raise CliError(f"map file not found: {path}")
    return map_path.read_text(encoding="utf-8")


_READY_AI = frozenset(
    {
        "manual",
        "random",
        "rulebased",
        "bfs",
        "dfs",
        "ucs",
        "greedy",
        "astar",
        "minimax",
        "alphabeta",
        "expectimax",
        "qlearning",
    }
)


def _check_ai_implemented(name: str, role_label: str) -> None:
    """Reject AI names that are not available in this build step."""
    key = name.lower().strip()
    if key in _READY_AI:
        return
    if key in AGENT_NAMES:
        raise CliError(
            f"{role_label} AI {name!r} is not implemented yet "
            f"(supported: {', '.join(sorted(_READY_AI))})"
        )
    raise CliError(f"unknown {role_label} AI {name!r}; choose one of: {', '.join(AGENT_NAMES)}")


def _first_ai(value: str) -> str:
    """Take the first name from a possibly comma-separated AI list."""
    return value.split(",")[0].strip().lower()


def config_from_args(args: argparse.Namespace) -> GameConfig:
    """Build a validated GameConfig from parsed CLI arguments."""
    if args.desktop:
        raise CliError("--desktop is not implemented yet (optional step 11)")
    # In compare mode the varied role may be a comma list; store the first as baseline.
    zombie_ai = _first_ai(args.zombie_ai)
    human_ai = _first_ai(args.human_ai)
    healer_ai = _first_ai(args.healer_ai)
    _check_ai_implemented(zombie_ai, "zombie")
    _check_ai_implemented(human_ai, "human")
    _check_ai_implemented(healer_ai, "healer")
    try:
        return GameConfig(
            map_text=_load_map_text(args.map_path),
            n_zombies=args.zombies,
            n_humans=args.humans,
            n_healers=args.healers,
            max_rounds=args.rounds,
            heal_cooldown=args.heal_cooldown,
            seed=args.seed,
            vision_radius=args.vision,
            hidden_roles=bool(args.hidden_roles),
            zombie_ai=zombie_ai,
            human_ai=human_ai,
            healer_ai=healer_ai,
            search_depth=args.depth,
            heuristic=args.heuristic,
            move_time_limit=5.0,
            node_budget=50_000,
        )
    except ValueError as exc:
        raise CliError(str(exc)) from exc


def _compare_names(args: argparse.Namespace) -> list[str]:
    """AI names to compare for the selected role (comma-separated)."""
    role = args.compare_role
    raw = {"zombie": args.zombie_ai, "human": args.human_ai, "healer": args.healer_ai}[role]
    names = [n.strip().lower() for n in raw.split(",") if n.strip()]
    if len(names) < 2:
        raise CliError(
            f"--compare needs a comma-separated --{role}-ai list with at least two names"
        )
    for name in names:
        _check_ai_implemented(name, role)
    return names


def run_compare_cli(args: argparse.Namespace, config: GameConfig) -> int:
    """Run compare mode and print a metrics table."""
    from evaluation.compare_mode import compare_agents, format_compare_table

    map_name = Path(args.map_path).stem
    rows = compare_agents(
        config,
        _compare_names(args),
        args.games,
        role=args.compare_role,
        map_name=map_name,
    )
    print(format_compare_table(rows))
    return 0


def build_controllers(config: GameConfig, engine: Engine) -> dict:
    """Create one agent controller per spawned agent id and role."""
    assert engine.state is not None
    controllers = {}
    for agent in engine.state.agents:
        if agent.role.value == "zombie":
            name = config.zombie_ai
        elif agent.role.value == "healer":
            name = config.healer_ai
        else:
            name = config.human_ai
        rng = private_rng(config.seed, agent.id)
        controllers[agent.id] = make_agent(name, agent.id, agent.role, config, rng)
    return controllers


def format_result(result: GameResult) -> str:
    """Format the final result as a short human-readable block."""
    return (
        f"winner={result.winner} reason={result.reason} rounds={result.rounds_played}\n"
        f"zombies={result.zombies} humans={result.humans} healers={result.healers} "
        f"infections={result.infections} heals={result.heals}"
    )


def run_headless(config: GameConfig, quiet: bool = False) -> GameResult:
    """Run one full game and optionally print the grid each round."""
    engine = Engine(config)
    engine.reset()
    engine.controllers = build_controllers(config, engine)
    last_round = 0
    if not quiet and engine.state is not None:
        print(f"=== round {engine.state.round_number} (start) ===")
        print(render_grid(engine.state))
        last_round = engine.state.round_number
    while engine.state is not None and not engine.state.done:
        engine.step()
        if not quiet and engine.state is not None and engine.state.round_number != last_round:
            print(f"=== round {engine.state.round_number} ===")
            print(render_grid(engine.state))
            last_round = engine.state.round_number
    assert engine.result is not None
    if not quiet and engine.state is not None:
        print("=== final ===")
        print(render_grid(engine.state))
    print(format_result(engine.result))
    return engine.result


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code (0 ok, 2 invalid args)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = config_from_args(args)
        if args.compare:
            return run_compare_cli(args, config)
        run_headless(config, quiet=bool(args.quiet))
        return 0
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""SearchAgent: role-specific behavior built on the pathfinding algorithms."""

from __future__ import annotations

import random
from collections import deque
from agents.base_agent import BaseAgent
from agents.belief_tracker import BeliefTracker
from game.entities import ACTION_DELTAS, MOVE_ACTIONS, Action, Role
from game.grid import Grid
from game.visibility import Observation, VisibleAgent
from search.heuristics import MazeDistance, heuristic_to_nearest
from search.informed import astar, greedy
from search.problem import PathProblem, SearchResult
from search.uninformed import bfs, dfs, ucs

Cell = tuple[int, int]


class SearchAgent(BaseAgent):
    """Uses BFS/DFS/UCS/Greedy/A* for chase/approach; humans flee via multi-source BFS."""

    def __init__(
        self,
        agent_id: int,
        algorithm: str,
        rng: random.Random,
        heuristic: str = "manhattan",
        *,
        use_belief_tracker: bool = True,
        hidden_roles: bool = False,
    ) -> None:
        """Create a search agent for one algorithm name and optional heuristic."""
        super().__init__(agent_id, algorithm)
        self.algorithm = algorithm.lower().strip()
        self.rng = rng
        self.heuristic = heuristic
        self.use_belief_tracker = use_belief_tracker
        self.hidden_roles = hidden_roles
        self._maze: MazeDistance | None = None
        self.belief: BeliefTracker | None = None

    def reset(self) -> None:
        """Clear stats and the belief tracker for a new game."""
        super().reset()
        self.belief = None

    def get_action(self, obs: Observation) -> Action:
        """Choose a role-specific action and append search stats."""
        if self.use_belief_tracker:
            if self.belief is None:
                self.belief = BeliefTracker(
                    obs.grid, self.agent_id, hidden_roles=self.hidden_roles
                )
            self.belief.update(obs)
        legal = set(obs.legal_actions)
        if obs.self_role == Role.ZOMBIE:
            action, result = self._zombie(obs, legal)
        elif obs.self_role == Role.HEALER:
            action, result = self._healer(obs, legal)
        else:
            action, result = self._human(obs, legal)
        if action not in legal:
            action = self._fallback(obs, legal)
        self._record_from_result(result)
        return action

    def _record_from_result(self, result: SearchResult | None) -> None:
        """Append stats from a SearchResult (or zeros)."""
        if result is None:
            self._record_stats()
            return
        self._record_stats(
            nodes_expanded=result.nodes_expanded,
            nodes_generated=result.nodes_generated,
            time_seconds=result.time_seconds,
            path_cost=result.cost if result.found else None,
            depth=len(result.actions) if result.found else None,
            max_frontier_size=result.max_frontier_size,
            algorithm=self.algorithm,
        )

    def _zombie(self, obs: Observation, legal: set[Action]) -> tuple[Action, SearchResult | None]:
        """Path toward a cell adjacent to a visible human; else use belief, else explore."""
        humans = [a for a in obs.visible_agents if a.role in (Role.HUMAN, Role.HEALER)]
        # Hidden roles: treat unknown visible agents as possible prey too.
        if not humans and self.hidden_roles:
            humans = [a for a in obs.visible_agents if a.role is None]
        if not humans:
            return self._zombie_from_belief(obs, legal)
        if any(_is_adjacent(obs.self_x, obs.self_y, h.x, h.y) for h in humans):
            if Action.STAY in legal:
                return Action.STAY, None
        goals = _adjacent_floor_cells(obs.grid, humans, blocked=_occupied(obs))
        if (obs.self_x, obs.self_y) in goals:
            if Action.STAY in legal:
                return Action.STAY, None
        if not goals:
            return self._zombie_from_belief(obs, legal)
        result = self._search(obs, goals)
        action = _first_action(result, legal, self.rng)
        return action, result

    def _zombie_from_belief(
        self, obs: Observation, legal: set[Action]
    ) -> tuple[Action, SearchResult | None]:
        """Chase most-likely prey cells from the belief tracker."""
        if self.belief is None:
            return self._explore(obs, legal), None
        prey = self.belief.prey_cells()
        if not prey:
            return self._explore(obs, legal), None
        blocked = _occupied(obs)
        goals: set[Cell] = set()
        for px, py in prey:
            if _is_adjacent(obs.self_x, obs.self_y, px, py) and Action.STAY in legal:
                return Action.STAY, None
            for nx, ny in obs.grid.neighbors(px, py):
                if (nx, ny) not in blocked:
                    goals.add((nx, ny))
        if not goals:
            return self._explore(obs, legal), None
        result = self._search(obs, goals)
        return _first_action(result, legal, self.rng), result

    def _human(self, obs: Observation, legal: set[Action]) -> tuple[Action, SearchResult | None]:
        """Flee: maximize distance to nearest zombie; else flee belief danger cells."""
        zombies = [a for a in obs.visible_agents if a.role == Role.ZOMBIE]
        if not zombies:
            return self._human_from_belief(obs, legal)
        dist_map, expanded, generated = _multi_source_distances(
            obs.grid, [(z.x, z.y) for z in zombies]
        )
        result = SearchResult(
            found=True,
            path=(),
            actions=(),
            cost=0.0,
            nodes_expanded=expanded,
            nodes_generated=generated,
            max_frontier_size=0,
            time_seconds=0.0,
        )
        action = _flee_action(obs, legal, dist_map, zombies, self.rng)
        return action, result

    def _human_from_belief(
        self, obs: Observation, legal: set[Action]
    ) -> tuple[Action, SearchResult | None]:
        """Flee multi-source distances from belief danger peaks."""
        if self.belief is None:
            return self._explore(obs, legal), None
        sources = self.belief.danger_sources()
        if not sources:
            return self._explore(obs, legal), None
        dist_map, expanded, generated = _multi_source_distances(obs.grid, sources)
        result = SearchResult(
            found=True,
            path=(),
            actions=(),
            cost=0.0,
            nodes_expanded=expanded,
            nodes_generated=generated,
            max_frontier_size=0,
            time_seconds=0.0,
        )
        # No concrete VisibleAgent zombies; avoid stepping onto high-danger adjacent cells.
        fake = [
            VisibleAgent(id=-1 - i, x=c[0], y=c[1], role=Role.ZOMBIE)
            for i, c in enumerate(sources[:4])
        ]
        action = _flee_action(obs, legal, dist_map, fake, self.rng)
        return action, result

    def _healer(self, obs: Observation, legal: set[Action]) -> tuple[Action, SearchResult | None]:
        """Heal when possible; else approach an isolated zombie; else flee like a human."""
        for action in MOVE_ACTIONS:
            if action not in legal:
                continue
            dx, dy = ACTION_DELTAS[action]
            tx, ty = obs.self_x + dx, obs.self_y + dy
            for other in obs.visible_agents:
                if other.role == Role.ZOMBIE and other.x == tx and other.y == ty:
                    return action, None

        zombies = [a for a in obs.visible_agents if a.role == Role.ZOMBIE]
        isolated = [
            z
            for z in zombies
            if all(
                (z.id == o.id) or abs(z.x - o.x) + abs(z.y - o.y) > 3
                for o in zombies
            )
        ]
        if isolated:
            goals = _adjacent_floor_cells(obs.grid, isolated, blocked=_occupied(obs))
            if goals:
                if (obs.self_x, obs.self_y) in goals:
                    return (Action.STAY if Action.STAY in legal else self._fallback(obs, legal)), None
                result = self._search(obs, goals)
                return _first_action(result, legal, self.rng), result
        if zombies:
            return self._human(obs, legal)
        # No visible zombies: approach believed zombie cells, else flee danger / explore.
        if self.belief is not None:
            danger = self.belief.danger_sources(threshold=0.1)
            if danger:
                blocked = _occupied(obs)
                goals: set[Cell] = set()
                for zx, zy in danger[:3]:
                    for nx, ny in obs.grid.neighbors(zx, zy):
                        if (nx, ny) not in blocked:
                            goals.add((nx, ny))
                if goals:
                    result = self._search(obs, goals)
                    return _first_action(result, legal, self.rng), result
        return self._human_from_belief(obs, legal)

    def _search(self, obs: Observation, goals: set[Cell]) -> SearchResult:
        """Run the configured algorithm toward any cell in goals."""
        blocked = _occupied(obs)
        # Do not block goal cells (they are empty approach squares).
        blocked = frozenset(c for c in blocked if c not in goals)
        problem = PathProblem(
            grid=obs.grid,
            start=(obs.self_x, obs.self_y),
            goal_test=lambda c, g=goals: c in g,
            blocked=blocked,
        )
        goal_list = list(goals)
        maze = self._maze_for(obs.grid)

        def h(cell: Cell) -> float:
            return heuristic_to_nearest(cell, goal_list, self.heuristic, maze)

        if self.algorithm == "bfs":
            return bfs(problem)
        if self.algorithm == "dfs":
            return dfs(problem)
        if self.algorithm == "ucs":
            return ucs(problem)
        if self.algorithm == "greedy":
            return greedy(problem, h)
        if self.algorithm == "astar":
            return astar(problem, h)
        return bfs(problem)

    def _maze_for(self, grid: Grid) -> MazeDistance:
        """Return a MazeDistance cache, rebuilding if the grid identity changes."""
        if self._maze is None or self._maze.grid is not grid:
            self._maze = MazeDistance(grid)
        return self._maze

    def _explore(self, obs: Observation, legal: set[Action]) -> Action:
        """Fall back to a random safest legal action."""
        return self._fallback(obs, legal)

    def _fallback(self, obs: Observation, legal: set[Action]) -> Action:
        """Pick among safest legal actions using the private RNG."""
        if not legal:
            return Action.STAY
        zombies = [a for a in obs.visible_agents if a.role == Role.ZOMBIE]
        if not zombies:
            return self.rng.choice(sorted(legal, key=lambda a: a.value))
        scored: list[tuple[int, Action]] = []
        for action in legal:
            dx, dy = ACTION_DELTAS[action]
            nx, ny = obs.self_x + dx, obs.self_y + dy
            danger = sum(1 for z in zombies if _is_adjacent(nx, ny, z.x, z.y))
            scored.append((danger, action))
        best = min(s for s, _ in scored)
        choices = [a for s, a in scored if s == best]
        return self.rng.choice(choices)


def _is_adjacent(x0: int, y0: int, x1: int, y1: int) -> bool:
    """Return True if the cells are orthogonally adjacent."""
    return abs(x0 - x1) + abs(y0 - y1) == 1


def _occupied(obs: Observation, exclude_self: bool = True) -> frozenset[Cell]:
    """Cells occupied by visible agents (and optionally treated as blocked)."""
    cells = {(a.x, a.y) for a in obs.visible_agents}
    if not exclude_self:
        cells.add((obs.self_x, obs.self_y))
    return frozenset(cells)


def _adjacent_floor_cells(
    grid: Grid, agents: list[VisibleAgent], blocked: frozenset[Cell]
) -> set[Cell]:
    """Floor cells orthogonally adjacent to any listed agent and not blocked."""
    goals: set[Cell] = set()
    for agent in agents:
        for nx, ny in grid.neighbors(agent.x, agent.y):
            if (nx, ny) not in blocked:
                goals.add((nx, ny))
    return goals


def _first_action(
    result: SearchResult, legal: set[Action], rng: random.Random
) -> Action:
    """Return the first path action if legal, else a random legal action."""
    if result.found and result.actions:
        action = result.actions[0]
        if action in legal:
            return action
    if not legal:
        return Action.STAY
    return rng.choice(sorted(legal, key=lambda a: a.value))


def _multi_source_distances(
    grid: Grid, sources: list[Cell]
) -> tuple[dict[Cell, int], int, int]:
    """Multi-source BFS distances from sources; returns (dist, expanded, generated)."""
    dist: dict[Cell, int] = {}
    queue: deque[Cell] = deque()
    for s in sources:
        if grid.is_floor(*s) and s not in dist:
            dist[s] = 0
            queue.append(s)
    expanded = 0
    generated = 0
    while queue:
        cell = queue.popleft()
        expanded += 1
        for nxt in grid.neighbors(*cell):
            generated += 1
            if nxt not in dist:
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
    return dist, expanded, generated


def _flee_action(
    obs: Observation,
    legal: set[Action],
    dist_map: dict[Cell, int],
    zombies: list[VisibleAgent],
    rng: random.Random,
) -> Action:
    """Pick the legal action maximizing zombie distance, then escapes, then lower terrain cost."""

    def adjacent_to_zombie(x: int, y: int) -> bool:
        return any(_is_adjacent(x, y, z.x, z.y) for z in zombies)

    candidates = list(legal)
    safe = []
    for action in candidates:
        dx, dy = ACTION_DELTAS[action]
        nx, ny = obs.self_x + dx, obs.self_y + dy
        if not adjacent_to_zombie(nx, ny):
            safe.append(action)
    pool = safe if safe else candidates

    def key(action: Action) -> tuple:
        dx, dy = ACTION_DELTAS[action]
        nx, ny = obs.self_x + dx, obs.self_y + dy
        zdist = dist_map.get((nx, ny), 0)
        escapes = sum(
            1
            for n in obs.grid.neighbors(nx, ny)
            if n not in _occupied(obs) and not adjacent_to_zombie(*n)
        )
        terrain = obs.grid.cost(nx, ny) if obs.grid.is_floor(nx, ny) else 99
        # Maximize zdist and escapes; minimize terrain. Tie-break via later RNG.
        return (zdist, escapes, -terrain)

    best = max(key(a) for a in pool)
    tied = [a for a in pool if key(a) == best]
    return rng.choice(tied)

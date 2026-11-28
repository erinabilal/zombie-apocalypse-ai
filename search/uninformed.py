"""Uninformed graph search: BFS, depth-limited DFS and UCS."""

from __future__ import annotations

import time
from collections import deque
from heapq import heappop, heappush

from game.entities import Action
from search.problem import PathProblem, SearchResult, reconstruct_path

Cell = tuple[int, int]


def bfs(problem: PathProblem) -> SearchResult:
    """Breadth-first search; optimal in number of steps."""
    t0 = time.perf_counter()
    start = problem.start
    if problem.is_goal(start):
        return SearchResult(True, (start,), (), 0.0, 0, 0, 1, time.perf_counter() - t0)

    frontier: deque[Cell] = deque([start])
    came_from: dict[Cell, tuple[Cell | None, Action | None]] = {start: (None, None)}
    g_cost: dict[Cell, float] = {start: 0.0}
    explored: set[Cell] = set()
    nodes_expanded = 0
    nodes_generated = 0
    max_frontier = 1

    while frontier:
        max_frontier = max(max_frontier, len(frontier))
        cell = frontier.popleft()
        if cell in explored:
            continue
        explored.add(cell)
        nodes_expanded += 1
        if problem.is_goal(cell):
            path, actions = reconstruct_path(came_from, start, cell)
            return SearchResult(
                True,
                path,
                actions,
                g_cost[cell],
                nodes_expanded,
                nodes_generated,
                max_frontier,
                time.perf_counter() - t0,
            )
        for action, nxt, step in problem.successors(cell):
            nodes_generated += 1
            if nxt in explored or nxt in came_from:
                continue
            came_from[nxt] = (cell, action)
            g_cost[nxt] = g_cost[cell] + step
            frontier.append(nxt)

    return SearchResult.failure(nodes_expanded, nodes_generated, max_frontier, time.perf_counter() - t0)


def dfs(problem: PathProblem, depth_limit: int | None = None) -> SearchResult:
    """Depth-limited DFS (graph search); not optimal. Default limit = width*height."""
    t0 = time.perf_counter()
    start = problem.start
    limit = problem.depth_limit() if depth_limit is None else depth_limit
    if problem.is_goal(start):
        return SearchResult(True, (start,), (), 0.0, 0, 0, 1, time.perf_counter() - t0)

    # Stack entries: (cell, depth)
    stack: list[tuple[Cell, int]] = [(start, 0)]
    came_from: dict[Cell, tuple[Cell | None, Action | None]] = {start: (None, None)}
    g_cost: dict[Cell, float] = {start: 0.0}
    explored: set[Cell] = set()
    nodes_expanded = 0
    nodes_generated = 0
    max_frontier = 1

    while stack:
        max_frontier = max(max_frontier, len(stack))
        cell, depth = stack.pop()
        if cell in explored:
            continue
        explored.add(cell)
        nodes_expanded += 1
        if problem.is_goal(cell):
            path, actions = reconstruct_path(came_from, start, cell)
            return SearchResult(
                True,
                path,
                actions,
                g_cost[cell],
                nodes_expanded,
                nodes_generated,
                max_frontier,
                time.perf_counter() - t0,
            )
        if depth >= limit:
            continue
        # Push successors in reverse so UP is tried first (LIFO).
        succ = problem.successors(cell)
        for action, nxt, step in reversed(succ):
            nodes_generated += 1
            if nxt in explored:
                continue
            if nxt not in came_from:
                came_from[nxt] = (cell, action)
                g_cost[nxt] = g_cost[cell] + step
            stack.append((nxt, depth + 1))

    return SearchResult.failure(nodes_expanded, nodes_generated, max_frontier, time.perf_counter() - t0)


def ucs(problem: PathProblem) -> SearchResult:
    """Uniform-cost search; optimal in path cost. Skips stale heap entries."""
    t0 = time.perf_counter()
    start = problem.start
    if problem.is_goal(start):
        return SearchResult(True, (start,), (), 0.0, 0, 0, 1, time.perf_counter() - t0)

    counter = 0
    # heap entries: (g, counter, cell)
    heap: list[tuple[float, int, Cell]] = [(0.0, counter, start)]
    came_from: dict[Cell, tuple[Cell | None, Action | None]] = {start: (None, None)}
    g_cost: dict[Cell, float] = {start: 0.0}
    explored: set[Cell] = set()
    nodes_expanded = 0
    nodes_generated = 0
    max_frontier = 1

    while heap:
        max_frontier = max(max_frontier, len(heap))
        g, _, cell = heappop(heap)
        if cell in explored:
            continue
        if g > g_cost.get(cell, float("inf")):
            continue  # stale
        explored.add(cell)
        nodes_expanded += 1
        if problem.is_goal(cell):
            path, actions = reconstruct_path(came_from, start, cell)
            return SearchResult(
                True,
                path,
                actions,
                g_cost[cell],
                nodes_expanded,
                nodes_generated,
                max_frontier,
                time.perf_counter() - t0,
            )
        for action, nxt, step in problem.successors(cell):
            nodes_generated += 1
            new_g = g + step
            if new_g < g_cost.get(nxt, float("inf")):
                g_cost[nxt] = new_g
                came_from[nxt] = (cell, action)
                counter += 1
                heappush(heap, (new_g, counter, nxt))

    return SearchResult.failure(nodes_expanded, nodes_generated, max_frontier, time.perf_counter() - t0)

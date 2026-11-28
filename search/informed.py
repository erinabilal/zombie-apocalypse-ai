"""Informed graph search: Greedy best-first and A*."""

from __future__ import annotations

import time
from collections.abc import Callable
from heapq import heappop, heappush

from game.entities import Action
from search.problem import PathProblem, SearchResult, reconstruct_path

Cell = tuple[int, int]
Heuristic = Callable[[Cell], float]


def greedy(problem: PathProblem, heuristic: Heuristic) -> SearchResult:
    """Greedy best-first search using h only; may be suboptimal."""
    t0 = time.perf_counter()
    start = problem.start
    if problem.is_goal(start):
        return SearchResult(True, (start,), (), 0.0, 0, 0, 1, time.perf_counter() - t0)

    counter = 0
    heap: list[tuple[float, int, Cell]] = [(heuristic(start), counter, start)]
    came_from: dict[Cell, tuple[Cell | None, Action | None]] = {start: (None, None)}
    g_cost: dict[Cell, float] = {start: 0.0}
    explored: set[Cell] = set()
    nodes_expanded = 0
    nodes_generated = 0
    max_frontier = 1

    while heap:
        max_frontier = max(max_frontier, len(heap))
        _, _, cell = heappop(heap)
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
            counter += 1
            heappush(heap, (heuristic(nxt), counter, nxt))

    return SearchResult.failure(nodes_expanded, nodes_generated, max_frontier, time.perf_counter() - t0)


def astar(problem: PathProblem, heuristic: Heuristic) -> SearchResult:
    """A* search (f = g + h); goal tested on pop; reopens if a better g is found."""
    t0 = time.perf_counter()
    start = problem.start
    if problem.is_goal(start):
        return SearchResult(True, (start,), (), 0.0, 0, 0, 1, time.perf_counter() - t0)

    counter = 0
    # heap: (f, g, counter, cell)
    g_cost: dict[Cell, float] = {start: 0.0}
    heap: list[tuple[float, float, int, Cell]] = [
        (heuristic(start), 0.0, counter, start)
    ]
    came_from: dict[Cell, tuple[Cell | None, Action | None]] = {start: (None, None)}
    closed: set[Cell] = set()
    nodes_expanded = 0
    nodes_generated = 0
    max_frontier = 1

    while heap:
        max_frontier = max(max_frontier, len(heap))
        f, g, _, cell = heappop(heap)
        if g > g_cost.get(cell, float("inf")):
            continue  # stale
        if cell in closed:
            continue
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
        closed.add(cell)
        for action, nxt, step in problem.successors(cell):
            nodes_generated += 1
            new_g = g + step
            if new_g < g_cost.get(nxt, float("inf")):
                g_cost[nxt] = new_g
                came_from[nxt] = (cell, action)
                if nxt in closed:
                    closed.discard(nxt)  # reopen for inconsistent heuristics
                counter += 1
                heappush(heap, (new_g + heuristic(nxt), new_g, counter, nxt))

    return SearchResult.failure(nodes_expanded, nodes_generated, max_frontier, time.perf_counter() - t0)

"""Pathfinding search: uninformed (BFS, DFS, UCS) and informed (Greedy, A*) with heuristics."""

from search.heuristics import MazeDistance, euclidean, manhattan
from search.informed import astar, greedy
from search.problem import PathProblem, SearchResult
from search.uninformed import bfs, dfs, ucs

__all__ = [
    "PathProblem",
    "SearchResult",
    "bfs",
    "dfs",
    "ucs",
    "greedy",
    "astar",
    "manhattan",
    "euclidean",
    "MazeDistance",
]

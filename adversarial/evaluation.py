"""evaluate(state, perspective): weighted state score using the WEIGHTS dict."""

from __future__ import annotations

from game.entities import Role
from game.state import GameState

# Positive terms favor the zombie team; human-team perspective negates the total.
WEIGHTS: dict[str, float] = {
    "win": 10000.0,
    "loss": -10000.0,
    "zombie_margin": 50.0,
    "infections": 20.0,
    "heals": -15.0,
    "threat": 8.0,
    "min_zh_dist": -3.0,
    "cornered": 12.0,
    "healer_ready": -10.0,
    "healer_dist": 4.0,
    "time_pressure": 0.5,
}


def evaluate(state: GameState, perspective: Role) -> float:
    """Return a score for perspective (zombie wants high; human/healer want high for their team)."""
    zombie_score = _zombie_team_score(state)
    if perspective == Role.ZOMBIE:
        return zombie_score
    return -zombie_score


def _zombie_team_score(state: GameState) -> float:
    """Score from the zombie team's point of view."""
    if state.done:
        if state.winner == "zombies":
            return WEIGHTS["win"]
        if state.winner == "humans":
            return WEIGHTS["loss"]
        return 0.0

    zombies = [a for a in state.agents if a.role == Role.ZOMBIE]
    humans = [a for a in state.agents if a.role.is_human_team()]
    healers = [a for a in state.agents if a.role == Role.HEALER]

    if not humans:
        return WEIGHTS["win"]
    if not zombies:
        return WEIGHTS["loss"]

    score = 0.0
    score += WEIGHTS["zombie_margin"] * (len(zombies) - len(humans))
    score += WEIGHTS["infections"] * state.infections
    score += WEIGHTS["heals"] * state.heals

    # Threat: sum 1/(1+d) for each human to nearest zombie.
    threat = 0.0
    min_zh = 10**9
    cornered = 0
    for h in humans:
        dists = [_manhattan(h.pos, z.pos) for z in zombies]
        d = min(dists)
        min_zh = min(min_zh, d)
        threat += 1.0 / (1.0 + d)
        escapes = 0
        occupied = state.occupied_cells()
        for nx, ny in state.grid.neighbors(h.x, h.y):
            if (nx, ny) not in occupied:
                escapes += 1
        if escapes < 2:
            cornered += 1
    score += WEIGHTS["threat"] * threat
    score += WEIGHTS["min_zh_dist"] * min_zh
    score += WEIGHTS["cornered"] * cornered

    if healers:
        healer = healers[0]
        score += WEIGHTS["healer_ready"] * (1.0 if healer.cooldown == 0 else 0.0)
        if zombies:
            hd = min(_manhattan(healer.pos, z.pos) for z in zombies)
            score += WEIGHTS["healer_dist"] * hd

    # Time pressure: fewer rounds left favors zombies slightly if they lead.
    rounds_left = max(0, state.max_rounds - state.round_number + 1)
    score += WEIGHTS["time_pressure"] * (state.max_rounds - rounds_left) * (
        1 if len(zombies) >= len(humans) else -1
    )
    return score


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Manhattan distance between two cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

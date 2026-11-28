"""GameState: fast copy() (no deepcopy), hashable key(), count(role), agent(id), occupied_cells()."""

from __future__ import annotations

from dataclasses import dataclass, replace

from game.entities import AgentState, Role
from game.grid import Grid


@dataclass(frozen=True)
class GameState:
    """Immutable full game snapshot used by the engine and by search."""

    grid: Grid
    agents: tuple[AgentState, ...]
    round_number: int
    current_index: int
    skipped: frozenset[int]
    acted: frozenset[int]
    infections: int
    heals: int
    illegal_actions: int
    max_rounds: int
    heal_cooldown: int
    done: bool = False
    winner: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        """Require agents sorted by ascending id."""
        ids = [agent.id for agent in self.agents]
        if ids != sorted(ids):
            raise ValueError("agents must be sorted by ascending id")
        if len(ids) != len(set(ids)):
            raise ValueError("agent ids must be unique")

    def copy(self) -> GameState:
        """Return a shallow copy suitable for mutation via replace (no deepcopy)."""
        return replace(
            self,
            agents=tuple(self.agents),
            skipped=frozenset(self.skipped),
            acted=frozenset(self.acted),
        )

    def key(self) -> tuple:
        """Return a hashable key for transposition / visited sets."""
        agent_key = tuple(
            (a.id, a.role.value, a.x, a.y, a.cooldown) for a in self.agents
        )
        return (
            agent_key,
            self.round_number,
            self.current_index,
            tuple(sorted(self.skipped)),
            tuple(sorted(self.acted)),
            self.infections,
            self.heals,
            self.illegal_actions,
            self.done,
            self.winner,
            self.reason,
        )

    def agent(self, agent_id: int) -> AgentState:
        """Return the agent with the given id, or raise KeyError."""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        raise KeyError(f"no agent with id {agent_id}")

    def agent_index(self, agent_id: int) -> int:
        """Return the index of the agent with the given id."""
        for index, agent in enumerate(self.agents):
            if agent.id == agent_id:
                return index
        raise KeyError(f"no agent with id {agent_id}")

    def replace_agent(self, updated: AgentState) -> GameState:
        """Return a state with one agent replaced by id."""
        agents = list(self.agents)
        index = self.agent_index(updated.id)
        agents[index] = updated
        return replace(self, agents=tuple(agents))

    def replace_agents(self, updates: dict[int, AgentState]) -> GameState:
        """Return a state with several agents replaced by id."""
        agents = list(self.agents)
        for agent_id, updated in updates.items():
            agents[self.agent_index(agent_id)] = updated
        return replace(self, agents=tuple(agents))

    def count(self, role: Role) -> int:
        """Return how many agents currently have the given role."""
        return sum(1 for agent in self.agents if agent.role == role)

    def count_human_team(self) -> int:
        """Return how many agents are on the human team (HUMAN + HEALER)."""
        return sum(1 for agent in self.agents if agent.role.is_human_team())

    def count_zombies(self) -> int:
        """Return how many agents are zombies."""
        return self.count(Role.ZOMBIE)

    def occupied_cells(self) -> frozenset[tuple[int, int]]:
        """Return the set of cells currently occupied by any agent."""
        return frozenset(agent.pos for agent in self.agents)

    def current_agent(self) -> AgentState | None:
        """Return the agent about to act, or None if the state is terminal / empty."""
        if self.done or not self.agents:
            return None
        if self.current_index < 0 or self.current_index >= len(self.agents):
            return None
        return self.agents[self.current_index]

    def with_terminal(self, winner: str, reason: str) -> GameState:
        """Return this state marked finished with the given winner and reason."""
        return replace(self, done=True, winner=winner, reason=reason)

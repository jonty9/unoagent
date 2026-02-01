"""Single game runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from unoagent.engine import (
    PlayerView,
    get_legal_actions,
    apply_action,
    init_game,
)
from unoagent.engine.rules import DrawCard

if TYPE_CHECKING:
    from unoagent.agent.protocol import AgentProtocol


@dataclass
class GameResult:
    """Result of a completed game."""

    winner: Optional[str]
    num_turns: int
    player_ids: tuple[str, ...]


class GameRunner:
    """Runs a single UNO game to completion."""

    def __init__(
        self,
        agents: dict[str, "AgentProtocol"],
        seed: Optional[int] = None,
        timeout_per_turn: float = 60.0,
    ):
        self._agents = agents
        self._seed = seed
        self._timeout = timeout_per_turn

    def run(self) -> GameResult:
        """Run the game and return the result."""
        player_ids = list(self._agents.keys())
        state = init_game(player_ids, seed=self._seed)
        num_turns = 0
        max_turns = 1000

        while state.winner is None and num_turns < max_turns:
            pid = state.current_player
            agent = self._agents[pid]
            legal = get_legal_actions(state, pid)
            if not legal:
                break

            player_view = PlayerView.from_state(state, pid)
            action = agent.get_action(player_view, legal, pid)

            if action is None:
                action = next((a for a in legal if isinstance(a, DrawCard)), legal[0])

            state = apply_action(state, pid, action)
            num_turns += 1

        return GameResult(
            winner=state.winner,
            num_turns=num_turns,
            player_ids=tuple(player_ids),
        )

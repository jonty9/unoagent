"""Agent protocol - interface that LLM and human agents implement."""

from typing import Protocol

from unoagent.engine import Action, PlayerView


class AgentProtocol(Protocol):
    """Interface for UNO-playing agents."""

    @property
    def name(self) -> str:
        """Display name for the agent."""
        ...

    def get_action(
        self,
        player_view: PlayerView,
        legal_actions: list[Action],
        player_id: str,
    ) -> Action | None:
        """Choose an action given the player view and legal actions.

        Args:
            player_view: Filtered view with only this player's hand and public info.
            legal_actions: List of valid actions to choose from.
            player_id: This agent's player ID.

        Returns:
            One of the legal actions, or None to draw (when DrawCard is legal).
        """
        ...

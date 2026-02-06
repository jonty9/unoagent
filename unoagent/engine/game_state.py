"""Game state for UNO."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from unoagent.engine.card import Card, Color


@dataclass(frozen=True)
class GameState:
    """Immutable UNO game state."""

    hands: Dict[str, List[Card]]  # player_id -> list of cards
    discard_pile: List[Card]  # top is last
    draw_pile: List[Card]
    current_player: str
    direction: int  # 1 = clockwise, -1 = counter-clockwise
    last_played_color: Optional[Color]  # for wild cards
    pending_draws: int  # accumulated Draw Two/Four
    winner: Optional[str] = None
    player_order: tuple[str, ...] = field(default_factory=tuple)
    history: tuple[str, ...] = field(default_factory=tuple)  # Log of events

    def top_discard(self) -> Optional[Card]:
        """Return the top card on the discard pile."""
        return self.discard_pile[-1] if self.discard_pile else None


@dataclass
class PlayerView:
    """Filtered game state visible to a single player.

    Contains only that player's hand and public info.
    """

    my_hand: List[Card]
    discard_pile: List[Card]
    top_discard: Optional[Card]
    current_player: str
    direction: int
    last_played_color: Optional[Color]
    pending_draws: int
    winner: Optional[str]
    player_order: tuple[str, ...]
    num_cards_per_player: Dict[str, int]  # player_id -> count (for others, not own)
    history: List[str]  # Recent game events

    @classmethod
    def from_state(cls, state: GameState, player_id: str) -> "PlayerView":
        """Create a player view from full game state, hiding other players' hands."""
        num_cards = {
            pid: len(cards) for pid, cards in state.hands.items()
        }
        return cls(
            my_hand=list(state.hands.get(player_id, [])),
            discard_pile=list(state.discard_pile),
            top_discard=state.top_discard(),
            current_player=state.current_player,
            direction=state.direction,
            last_played_color=state.last_played_color,
            pending_draws=state.pending_draws,
            winner=state.winner,
            player_order=state.player_order,
            num_cards_per_player=num_cards,
            history=list(state.history[-10:]),  # Last 10 events
        )

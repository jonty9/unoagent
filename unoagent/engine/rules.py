"""UNO rules: legal actions and state transitions."""

import random
from dataclasses import dataclass
from typing import List, Optional, Union

from unoagent.engine.card import Card, Color
from unoagent.engine.game_state import GameState


@dataclass
class PlayCard:
    """Action: play a card. For wilds, chosen_color is required."""

    card: Card
    chosen_color: Optional[Color] = None


@dataclass
class DrawCard:
    """Action: draw a card (when no legal play or player chooses to draw)."""

    pass


Action = Union[PlayCard, DrawCard]


def init_game(
    player_ids: List[str],
    seed: Optional[int] = None,
) -> GameState:
    """Create initial game state: deal 7 cards each, one card on discard."""
    from unoagent.engine.deck import create_deck

    deck = create_deck(seed=seed)
    hands: dict[str, list[Card]] = {pid: [] for pid in player_ids}
    for _ in range(7):
        for pid in player_ids:
            if deck:
                hands[pid].append(deck.pop())
    # First card: must not be wild; put one non-wild on discard
    first_card = None
    wilds = []
    while deck:
        card = deck.pop()
        if card.value in ("wild", "wild_draw_four"):
            wilds.append(card)
        else:
            first_card = card
            break
    deck.extend(wilds)
    discard = [first_card] if first_card else ([deck.pop()] if deck else [])
    top = discard[-1] if discard else None
    last_color = top.color if top and top.color else Color.RED
    return GameState(
        hands=hands,
        discard_pile=discard,
        draw_pile=deck,
        current_player=player_ids[0],
        direction=1,
        last_played_color=last_color,
        pending_draws=0,
        player_order=tuple(player_ids),
    )


def _effective_color(state: GameState) -> Color:
    """Color that must be matched (top discard or last played for wild)."""
    top = state.top_discard()
    if top is None:
        raise ValueError("No card on discard pile")
    if top.color is not None:
        return top.color
    return state.last_played_color or Color.RED  # fallback


def _card_matches(card: Card, state: GameState) -> bool:
    """Check if a card can be played on the current discard pile."""
    top = state.top_discard()
    if top is None:
        return False
    eff_color = _effective_color(state)
    # Wild can always be played
    if card.value in ("wild", "wild_draw_four"):
        return True
    # Match by color
    if card.color == eff_color:
        return True
    # Match by value
    if card.value == top.value:
        return True
    return False


def get_legal_actions(state: GameState, player_id: str) -> List[Action]:
    """Return all legal actions for the current player."""
    if state.winner is not None:
        return []
    if state.current_player != player_id:
        return []

    # When pending draws, must draw (no stacking for now)
    if state.pending_draws > 0:
        return [DrawCard()]

    hand = state.hands.get(player_id, [])
    top = state.top_discard()

    if top is None:
        # First card - any card can be played; for simplicity, allow any
        actions: List[Action] = []
        for card in hand:
            if card.value in ("wild", "wild_draw_four"):
                for color in Color:
                    actions.append(PlayCard(card=card, chosen_color=color))
            else:
                actions.append(PlayCard(card=card))
        actions.append(DrawCard())
        return actions

    playable = [c for c in hand if _card_matches(c, state)]

    actions = []
    for card in playable:
        if card.value in ("wild", "wild_draw_four"):
            for color in Color:
                actions.append(PlayCard(card=card, chosen_color=color))
        else:
            actions.append(PlayCard(card=card))

    # Can always draw if we have no play or choose to
    actions.append(DrawCard())

    return actions


def apply_action(state: GameState, player_id: str, action: Action) -> GameState:
    """Apply an action and return the new game state."""
    if state.winner is not None:
        return state

    hands = dict(state.hands)
    discard = list(state.discard_pile)
    draw = list(state.draw_pile)
    current = state.current_player
    direction = state.direction
    last_color = state.last_played_color
    pending = state.pending_draws
    order = state.player_order
    history = list(state.history)

    if isinstance(action, DrawCard):
        # Draw cards for pending draws first
        if pending > 0:
            for _ in range(pending):
                if not draw and discard:
                    top = discard[-1]
                    draw = list(discard[:-1])
                    random.shuffle(draw)
                    discard = [top]
                if draw:
                    hands[player_id] = hands[player_id] + [draw.pop()]
            pending = 0
            # Skip turn after drawing (no play)
            idx = order.index(current)
            current = order[(idx + direction) % len(order)]
            history.append(f"{player_id} drew {len(hands[player_id]) - len(state.hands[player_id])} cards (penalty)")
            return GameState(
                hands=hands,
                discard_pile=discard,
                draw_pile=draw,
                current_player=current,
                direction=direction,
                last_played_color=last_color,
                pending_draws=pending,
                player_order=order,
                history=tuple(history),
            )

        # Regular draw: draw one
        if not draw and discard:
            # Reshuffle discard (except top) into draw pile
            top = discard[-1]
            draw = list(discard[:-1])
            random.shuffle(draw)
            discard = [top]
        if draw:
            new_card = draw.pop()
            hands[player_id] = hands[player_id] + [new_card]
        # After draw, turn passes (simplified: no "play the drawn card" for now)
        idx = order.index(current)
        current = order[(idx + direction) % len(order)]
        history.append(f"{player_id} drew a card")
        return GameState(
            hands=hands,
            discard_pile=discard,
            draw_pile=draw,
            current_player=current,
            direction=direction,
            last_played_color=last_color,
            pending_draws=pending,
            player_order=order,
            history=tuple(history),
        )

    # PlayCard
    play = action
    if play.chosen_color is None and play.card.value in ("wild", "wild_draw_four"):
        raise ValueError("Wild card requires chosen_color")

    hand = list(hands[player_id])
    # Remove one matching card
    removed = False
    for i, c in enumerate(hand):
        if c.color == play.card.color and c.value == play.card.value:
            hand.pop(i)
            removed = True
            break
    if not removed:
        raise ValueError(f"Card {play.card} not in hand")

    hands[player_id] = hand
    discard.append(play.card)
    last_color = play.card.color if play.card.color is not None else play.chosen_color

    # Check win
    if len(hand) == 0:
        history.append(f"{player_id} played {play.card} and WON!")
        return GameState(
            hands=hands,
            discard_pile=discard,
            draw_pile=draw,
            current_player=current,
            direction=direction,
            last_played_color=last_color,
            pending_draws=pending,
            winner=player_id,
            player_order=order,
            history=tuple(history),
        )

    action_desc = f"{player_id} played {play.card}"
    if play.chosen_color:
        action_desc += f" (chose {play.chosen_color.value})"
    history.append(action_desc)

    # Handle special cards
    next_idx = (order.index(current) + direction) % len(order)
    next_player = order[next_idx]

    if play.card.value == "skip":
        next_idx = (next_idx + direction) % len(order)
        next_player = order[next_idx]
    elif play.card.value == "reverse":
        direction = -direction
        next_idx = (order.index(current) + direction) % len(order)
        next_player = order[next_idx]
    elif play.card.value == "draw_two":
        # Next player draws 2, turn skips to player after
        skipped = order[next_idx]
        for _ in range(2):
            if not draw and discard:
                top = discard[-1]
                draw = list(discard[:-1])
                random.shuffle(draw)
                discard = [top]
            if draw:
                hands[skipped] = hands[skipped] + [draw.pop()]
        next_idx = (next_idx + direction) % len(order)
        next_player = order[next_idx]
    elif play.card.value == "wild_draw_four":
        # Next player draws 4, turn skips to player after
        skipped = order[next_idx]
        for _ in range(4):
            if not draw and discard:
                top = discard[-1]
                draw = list(discard[:-1])
                random.shuffle(draw)
                discard = [top]
            if draw:
                hands[skipped] = hands[skipped] + [draw.pop()]
        next_idx = (next_idx + direction) % len(order)
        next_player = order[next_idx]

    return GameState(
        hands=hands,
        discard_pile=discard,
        draw_pile=draw,
        current_player=next_player,
        direction=direction,
        last_played_color=last_color,
        pending_draws=pending,
        player_order=order,
        history=tuple(history),
    )

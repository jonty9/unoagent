"""Deck creation and shuffling."""

import random
from typing import List

from unoagent.engine.card import Card, Color

CARD_VALUES_STANDARD = (
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "skip", "reverse", "draw_two",
)


def create_deck(seed: int | None = None) -> List[Card]:
    """Create a standard 108-card UNO deck.

    - 4 colors × (0-9, Skip, Reverse, Draw Two): 76 cards
    - 4 Wild, 4 Wild Draw Four: 8 cards
    - Total: 108 cards
    """
    cards: List[Card] = []

    for color in Color:
        # One zero per color
        cards.append(Card(color=color, value="0"))
        # Two of each 1-9 and action cards per color
        for value in CARD_VALUES_STANDARD[1:]:  # skip "0"
            cards.append(Card(color=color, value=value))
            cards.append(Card(color=color, value=value))

    for _ in range(4):
        cards.append(Card(color=None, value="wild"))
        cards.append(Card(color=None, value="wild_draw_four"))

    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(cards)
    else:
        random.shuffle(cards)

    return cards

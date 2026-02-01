"""Card and Color types for UNO."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Color(str, Enum):
    """Card colors."""

    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"


CARD_VALUES = (
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "skip", "reverse", "draw_two",
    "wild", "wild_draw_four",
)


@dataclass(frozen=True)
class Card:
    """A UNO card.

    For number/action cards: color is set, value is "0"-"9", "skip", "reverse", "draw_two".
    For wild cards: color is None, value is "wild" or "wild_draw_four".
    """

    color: Optional[Color]
    value: str

    def __post_init__(self) -> None:
        if self.value not in CARD_VALUES:
            raise ValueError(f"Invalid card value: {self.value}")
        if self.value in ("wild", "wild_draw_four") and self.color is not None:
            raise ValueError("Wild cards must have color=None")
        if self.value not in ("wild", "wild_draw_four") and self.color is None:
            raise ValueError("Non-wild cards must have a color")

    def __str__(self) -> str:
        if self.color is None:
            return self.value
        return f"{self.color.value}_{self.value}"

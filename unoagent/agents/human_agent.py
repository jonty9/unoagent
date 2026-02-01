"""Human agent - reads actions from terminal."""

from unoagent.engine import Action, Color
from unoagent.engine.rules import DrawCard, PlayCard


class HumanAgent:
    """Agent that prompts the human for input via terminal."""

    def __init__(self, name: str = "human"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def get_action(
        self,
        player_view,
        legal_actions: list[Action],
        player_id: str,
    ) -> Action | None:
        if not legal_actions:
            return None

        print("\n--- Your turn ---")
        print("Your hand:", " ".join(str(c) for c in player_view.my_hand))
        print("Top discard:", player_view.top_discard)
        print("\nLegal actions:")
        for i, a in enumerate(legal_actions):
            if isinstance(a, DrawCard):
                print(f"  {i}: DRAW")
            else:
                extra = f" (choose color: {a.chosen_color})" if a.chosen_color else ""
                print(f"  {i}: PLAY {a.card}{extra}")

        while True:
            try:
                raw = input("Enter number: ").strip()
                idx = int(raw)
                if 0 <= idx < len(legal_actions):
                    return legal_actions[idx]
            except (ValueError, EOFError):
                pass
            print("Invalid. Try again.")

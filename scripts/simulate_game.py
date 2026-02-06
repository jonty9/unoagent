"""Simulate a game with random agents."""

import random
from unoagent.engine import PlayerView, Action
from unoagent.engine.rules import DrawCard, PlayCard
from unoagent.orchestration.game_runner import GameRunner

class RandomAgent:
    def __init__(self, name):
        self.name = name

    def get_action(self, view: PlayerView, actions: list[Action], player_id: str) -> Action | None:
        if not actions:
            return None
        
        # Log the last move from history to see the game progress
        if view.history:
            print(f"> {view.history[-1]}")

        # Prefer playing over drawing to make game progress
        play_actions = [a for a in actions if isinstance(a, PlayCard)]
        if play_actions:
            return random.choice(play_actions)
        return random.choice(actions)

def main():
    agents = {
        "p1": RandomAgent("Bot1"),
        "p2": RandomAgent("Bot2"),
        "p3": RandomAgent("Bot3"),
        "p4": RandomAgent("Bot4"),
    }
    
    runner = GameRunner(agents, seed=42)
    result = runner.run()
    
    print(f"Game finished! Winner: {result.winner}")
    print(f"Turns: {result.num_turns}")
    
    # You can also inspect the history here if needed:
    # state = runner._last_state # (if you modify GameRunner to store it)

if __name__ == "__main__":
    main()

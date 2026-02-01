"""Tournament - run many games and aggregate results."""

import random
from collections import defaultdict
from typing import Any

from unoagent.orchestration.game_runner import GameRunner, GameResult


def run_tournament(
    agents: dict[str, Any],
    num_games: int = 100,
    seed: int | None = None,
) -> dict[str, int]:
    """Run a tournament: each agent plays each other agent.

    For 2 agents, they play num_games against each other.
    For more agents, we do round-robin style: each pair plays.
    Simplified: we alternate who goes first.

    Returns:
        Dict mapping agent/player_id to number of wins.
    """
    player_ids = list(agents.keys())
    wins: dict[str, int] = defaultdict(int)

    rng = random.Random(seed)
    for g in range(num_games):
        # Shuffle order for this game
        order = player_ids if g % 2 == 0 else list(reversed(player_ids))
        ordered_agents = {pid: agents[pid] for pid in order}
        runner = GameRunner(ordered_agents, seed=rng.randint(0, 2**31 - 1))
        result = runner.run()
        if result.winner:
            wins[result.winner] += 1

    return dict(wins)

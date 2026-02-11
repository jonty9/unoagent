"""CLI entry point."""

from __future__ import annotations

from typing import Optional

import typer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(help="UNO game with LLM and human agents")


def _parse_agents(
    agent_specs: str,
    llm_provider: str,
    llm_model: str,
) -> dict[str, "AgentProtocol"]:
    from unoagent.agent.protocol import AgentProtocol
    from unoagent.agents.human_agent import HumanAgent
    from unoagent.agents.llm_agent import LLMAgent

    parts = [s.strip().lower() for s in agent_specs.split(",") if s.strip()]
    agents: dict[str, AgentProtocol] = {}
    for i, part in enumerate(parts):
        pid = f"player_{i}"
        if ":" in part:
            kind, model = part.split(":", 1)
        else:
            kind, model = part, llm_model

        if kind == "llm":
            agents[pid] = LLMAgent(provider=llm_provider, model=model)
        elif kind == "human":
            agents[pid] = HumanAgent(name=f"Human_{i}")
        else:
            raise typer.BadParameter(f"Unknown agent type: {kind}. Use 'llm' or 'human'.")
    return agents


@app.command()
def play(
    agents: str = typer.Option(
        "llm,llm,llm,llm",
        "--agents",
        "-a",
        help="Comma-separated: llm, human, or llm:model_name (e.g. llm:gpt-4o,human,llm:llama3)",
    ),
    llm_provider: str = typer.Option(
        "openrouter",
        "--llm-provider",
        "-p",
        help="LLM provider: openrouter, groq, or ollama",
    ),
    llm_model: str = typer.Option(
        "openai/gpt-4o-mini",
        "--llm-model",
        "-m",
        help="Model name (e.g. openai/gpt-4o-mini, meta-llama/llama-3-8b-instruct)",
    ),
    seed: Optional[int] = typer.Option(None, "--seed", "-s", help="Random seed"),
) -> None:
    """Run a single UNO game."""
    from unoagent.orchestration.game_runner import GameRunner

    agent_map = _parse_agents(agents, llm_provider, llm_model)
    runner = GameRunner(agent_map, seed=seed)
    result = runner.run()
    typer.echo(f"Winner: {result.winner or 'None (draw)'}")
    typer.echo(f"Turns: {result.num_turns}")


@app.command()
def tournament(
    agents: str = typer.Option(
        "llm,llm",
        "--agents",
        "-a",
        help="Comma-separated agent types or llm:model_name (e.g. llm:gpt-4o,llm:llama3)",
    ),
    games: int = typer.Option(100, "--games", "-g", help="Number of games"),
    llm_provider: str = typer.Option(
        "openrouter",
        "--llm-provider",
        "-p",
        help="LLM provider: openrouter, groq, or ollama",
    ),
    llm_model: str = typer.Option(
        "openai/gpt-4o-mini",
        "--llm-model",
        "-m",
        help="Model name",
    ),
    seed: Optional[int] = typer.Option(None, "--seed", "-s", help="Random seed"),
) -> None:
    """Run a tournament."""
    from unoagent.orchestration.tournament import run_tournament

    agent_map = _parse_agents(agents, llm_provider, llm_model)
    wins = run_tournament(agent_map, num_games=games, seed=seed)
    typer.echo("Tournament results:")
    for pid, w in sorted(wins.items(), key=lambda x: -x[1]):
        typer.echo(f"  {pid}: {w} wins")


if __name__ == "__main__":
    app()

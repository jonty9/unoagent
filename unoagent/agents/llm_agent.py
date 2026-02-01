"""LLM agent using OpenAI library with OpenRouter or Groq."""

import json
import os
from typing import Optional

from openai import OpenAI

from unoagent.engine import Action, Color, PlayerView
from unoagent.engine.rules import DrawCard, PlayCard

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GROQ_BASE = "https://api.groq.com/openai/v1"


def _format_player_view(pv: PlayerView, player_id: str) -> str:
    """Format player view as text for the LLM."""
    lines = [
        "=== Your hand ===",
        " ".join(str(c) for c in pv.my_hand),
        "",
        "=== Top card on discard ===",
        str(pv.top_discard) if pv.top_discard else "None",
        "",
        "=== Current color to match ===",
        pv.last_played_color.value.upper() if pv.last_played_color else "any",
        "",
        "=== Other players' card counts ===",
    ]
    for pid, count in pv.num_cards_per_player.items():
        if pid != player_id:
            lines.append(f"  {pid}: {count} cards")
    lines.extend([
        "",
        "=== Direction ===",
        "clockwise" if pv.direction == 1 else "counter-clockwise",
        "",
        "=== Current player ===",
        pv.current_player,
        "",
        "=== Pending draws (for next player) ===",
        str(pv.pending_draws),
    ])
    return "\n".join(lines)


def _format_legal_actions(actions: list[Action]) -> str:
    """Format legal actions as text."""
    options = []
    for i, a in enumerate(actions):
        if isinstance(a, DrawCard):
            options.append(f"{i}: DRAW")
        else:
            card = a.card
            color = f" color={a.chosen_color}" if a.chosen_color else ""
            options.append(f"{i}: PLAY {card}{color}")
    return "\n".join(options)


def _parse_action_response(response: str, actions: list[Action]) -> Action | None:
    """Parse LLM response into an Action."""
    response = response.strip().upper()
    # Try to extract a number
    for word in response.replace(",", " ").split():
        if word.isdigit():
            idx = int(word)
            if 0 <= idx < len(actions):
                return actions[idx]
    # Try "DRAW" literally
    if "DRAW" in response:
        for a in actions:
            if isinstance(a, DrawCard):
                return a
    return None


class LLMAgent:
    """Agent that uses an LLM to choose actions."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "openai/gpt-4o-mini",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        if provider == "openrouter":
            base_url = OPENROUTER_BASE
            key = api_key or os.environ.get("OPENROUTER_API_KEY")
        elif provider == "groq":
            base_url = GROQ_BASE
            key = api_key or os.environ.get("GROQ_API_KEY")
        else:
            raise ValueError(f"Unknown provider: {provider}")

        if not key:
            raise ValueError(f"API key required for {provider}. Set {provider.upper()}_API_KEY or pass api_key.")

        self._client = OpenAI(api_key=key, base_url=base_url)
        self._model = model
        self._timeout = timeout
        self._provider = provider

    @property
    def name(self) -> str:
        return f"llm-{self._model}"

    def get_action(
        self,
        player_view: PlayerView,
        legal_actions: list[Action],
        player_id: str,
    ) -> Action | None:
        if not legal_actions:
            return None

        prompt = f"""You are playing UNO. Choose your action by responding with ONLY the number of your choice (0 to {len(legal_actions)-1}).

{_format_player_view(player_view, player_id)}

=== Legal actions (respond with the number) ===
{_format_legal_actions(legal_actions)}

Respond with a single number:"""

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self._timeout,
            )
            content = resp.choices[0].message.content or ""
            action = _parse_action_response(content, legal_actions)
            if action is None:
                # Fallback: pick first DrawCard or first action
                for a in legal_actions:
                    if isinstance(a, DrawCard):
                        return a
                return legal_actions[0]
            return action
        except Exception:
            # Fallback on error
            for a in legal_actions:
                if isinstance(a, DrawCard):
                    return a
            return legal_actions[0]

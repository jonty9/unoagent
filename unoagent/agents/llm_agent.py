"""LLM agent using OpenAI library with OpenRouter or Groq."""

import json
import os
from typing import Optional

from openai import OpenAI

from unoagent.engine import Action, Color, PlayerView
from unoagent.engine.rules import DrawCard, PlayCard

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GROQ_BASE = "https://api.groq.com/openai/v1"
OLLAMA_BASE = "http://localhost:11434/v1"
HUGGINGFACE_BASE = "https://router.huggingface.co/v1"


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
        "",
        "=== Game History (last 10 events) ===",
    ])
    if pv.history:
        lines.extend(f"- {h}" for h in pv.history)
    else:
        lines.append("No history yet.")
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
    # Try parsing JSON first
    try:
        # Strip markdown code blocks if present
        clean_resp = response.strip()
        if clean_resp.startswith("```"):
            clean_resp = clean_resp.strip("`")
            if clean_resp.startswith("json"):
                clean_resp = clean_resp[4:]
        
        data = json.loads(clean_resp)
        if isinstance(data, dict) and "action_index" in data:
            idx = data["action_index"]
            if 0 <= idx < len(actions):
                return actions[idx]
    except json.JSONDecodeError:
        pass

    # Fallback to heuristic parsing
    response = response.strip().upper()
    # Try to extract a number
    import re
    # Look for "action_index": N or just N
    match = re.search(r'"action_index"\s*:\s*(\d+)', response)
    if match:
        idx = int(match.group(1))
        if 0 <= idx < len(actions):
            return actions[idx]

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
        elif provider == "ollama":
            base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE)
            key = "ollama"
        elif provider == "huggingface":
            base_url = HUGGINGFACE_BASE
            key = api_key or os.environ.get("HUGGINGFACE_API_KEY")
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # For Ollama, key is "ollama" which is truthy, so this check passes
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

        prompt = f"""You are playing UNO.
Objective: Win by playing all your cards correctly. match the top discard card by color (Red, Blue, Green, Yellow) or value (0-9, Skip, Reverse, Draw Two). Wild cards can be played on anything.

{_format_player_view(player_view, player_id)}

=== Legal actions ===
{_format_legal_actions(legal_actions)}

INSTRUCTIONS:
Select the best action to win the game.
Analyze the game history and board state.
Respond with a JSON object containing the index of your chosen action.
Example: {{"action_index": 2}}
"""

        for attempt in range(3):
            try:
                kwargs = {
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "timeout": self._timeout,
                }
                
                # Only pass response_format if we know the provider supports it and we want JSON mode
                if "gpt-4" in self._model or "gpt-3.5" in self._model or "groq" in self._provider:
                     kwargs["response_format"] = {"type": "json_object"}

                resp = self._client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                action = _parse_action_response(content, legal_actions)
                if action is not None:
                    return action
                
                # If parsed action is None, try again but maybe log it?
                print(f"[{self.name}] Failed to parse action: {content[:100]}...")
            except Exception as e:
                print(f"[{self.name}] Error on attempt {attempt}: {e}")

        # Fallback after retries
        print(f"[{self.name}] All retries failed. Defaulting to draw/first action.")
        for a in legal_actions:
            if isinstance(a, DrawCard):
                return a
        return legal_actions[0]

"""LLM agent using OpenAI library with OpenRouter or Groq."""

import json
import os
import time
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
    import re

    # 1. Try to find a JSON-like object in the response
    # We'll be more aggressive and try to handle single quotes by replacing them
    json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        # Try strict JSON first
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "action_index" in data:
                idx = data["action_index"]
                if 0 <= idx < len(actions):
                    return actions[idx]
                print(f"[_parse_action_response] Index {idx} out of range (0-{len(actions)-1})")
        except (json.JSONDecodeError, ValueError):
            # Try a fuzzy parse for single quotes: {'key': 'val'} -> {"key": "val"}
            try:
                # This is a very basic fix for single quotes in simple objects
                fuzzy_str = json_str.replace("'", '"')
                data = json.loads(fuzzy_str)
                if isinstance(data, dict) and "action_index" in data:
                    idx = data["action_index"]
                    if 0 <= idx < len(actions):
                        return actions[idx]
                    print(f"[_parse_action_response] Index {idx} out of range (0-{len(actions)-1})")
            except Exception:
                pass

    # 2. Targeted regex for "action_index": N (Support both ' and " and no quotes)
    # Matches: "action_index": 1, 'action_index': 1, action_index: 1
    match = re.search(r'["\']?action_index["\']?\s*:\s*(\d+)', response, re.IGNORECASE)
    if match:
        idx = int(match.group(1))
        if 0 <= idx < len(actions):
            return actions[idx]
        print(f"[_parse_action_response] Index {idx} out of range (0-{len(actions)-1}) from regex")

    # 3. Fallback: Look for "DRAW" literally
    if "DRAW" in response.upper():
        for a in actions:
            if isinstance(a, DrawCard):
                return a
    
    # 4. Last resort: Try to find a standalone number
    # Clean up punctuation that commonly sticks to numbers in chatty responses
    cleaned_response = re.sub(r'[{}\[\]"\'.,:]', ' ', response)
    for word in cleaned_response.split():
        if word.isdigit():
            idx = int(word)
            if 0 <= idx < len(actions):
                return actions[idx]

    return None


class LLMAgent:
    """Agent that uses an LLM to choose actions."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "openai/gpt-4o-mini",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        rate_limit: Optional[float] = None,
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
        self._rate_limit = rate_limit  # Requests per minute
        self._request_history: list[float] = []

        print(f"[{self.name}] Initialized with provider={provider}, base_url={base_url}, timeout={timeout}s, rate_limit={rate_limit or 'None'} rpm")

    @property
    def name(self) -> str:
        return f"llm-{self._model}"

    def _wait_for_rate_limit(self):
        """Block if rate limit is exceeded."""
        if not self._rate_limit:
            return

        now = time.time()
        # Filter history to last 60 seconds
        self._request_history = [t for t in self._request_history if now - t < 60.0]

        if len(self._request_history) >= self._rate_limit:
            # Wait until the oldest request in the window expires
            oldest = self._request_history[0]
            wait_time = 60.0 - (now - oldest)
            if wait_time > 0:
                print(f"[{self.name}] Rate limit reached ({len(self._request_history)}/{self._rate_limit} rpm). Waiting {wait_time:.2f}s...")
                time.sleep(wait_time)
        
        self._request_history.append(time.time())

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

        for attempt in range(1, 4):
            try:
                self._wait_for_rate_limit()

                kwargs = {
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "timeout": self._timeout,
                }
                
                # Only pass response_format if we know the provider supports it and we want JSON mode
                if "gpt-4" in self._model or "gpt-3.5" in self._model or "groq" in self._provider:
                     kwargs["response_format"] = {"type": "json_object"}

                start_time = time.time()
                print(f"[{self.name}] Attempt {attempt}: Sending request to {self._provider} (timeout={self._timeout}s)...")
                
                resp = self._client.chat.completions.create(**kwargs)
                
                duration = time.time() - start_time
                content = resp.choices[0].message.content or ""
                print(f"[{self.name}] Received response in {duration:.2f}s")
                
                action = _parse_action_response(content, legal_actions)
                if action is not None:
                    return action
                
                print(f"[{self.name}] Failed to parse action from response:")
                print("-" * 40)
                print(content)
                print("-" * 40)
                print("Available actions:")
                print(_format_legal_actions(legal_actions))
                print("-" * 40)
            except Exception as e:
                duration = time.time() - start_time
                print(f"[{self.name}] Error on attempt {attempt} after {duration:.2f}s: {type(e).__name__}: {e}")

        # Fallback after retries
        print(f"[{self.name}] All retries failed. Defaulting to draw/first action.")
        for a in legal_actions:
            if isinstance(a, DrawCard):
                return a
        return legal_actions[0]

# UNO Agent

UNO game platform where LLM agents (via OpenRouter/Groq) and optionally a human player can play against each other.

## Setup

```bash
git clone <repo-url>
cd unoagent
uv sync   # or: pip install -e .
```

## Environment

For LLM agents, set one of:
- `OPENROUTER_API_KEY` (when using OpenRouter)
- `GROQ_API_KEY` (when using Groq)

## Usage

```bash
# Single game: 4 LLM players
unoagent play --agents llm,llm,llm,llm

# Human vs LLMs
unoagent play --agents human,llm,llm,llm

# Tournament
unoagent tournament --agents llm,llm --games 100
```

LLM options: `--llm-provider` (openrouter|groq), `--llm-model`

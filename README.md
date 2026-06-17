# My Kitchen

Personal, self-hosted recipe generator for one household. Flask + SQLite,
LLM generation via a swappable provider adapter (mock / Anthropic / Gemini).

## Quickstart
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and set `SECRET_KEY`
4. `python run.py` then open http://<host>:8000/

Runs on a Raspberry Pi 4 on the local network. See the design spec for scope.

# Sahaay (सहाय)

AI companion for government services in Delhi. Start with [CLAUDE.md](CLAUDE.md), then [docs/BACKLOG.md](docs/BACKLOG.md).

## Run locally

Needs Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 20+ + pnpm.

```bash
cp .env.example .env            # optional for now: the app runs on a stub LLM without a key

# backend (http://localhost:8000)
cd backend && uv run fastapi dev app/main.py

# frontend (http://localhost:3000), in a second terminal
cd frontend && pnpm install && pnpm dev
```

Browser tests (start their own servers on ports 8100 and 3100, no keys needed): `cd frontend && pnpm exec playwright install chromium && pnpm e2e`. If Chromium is already installed elsewhere, set `PW_CHROMIUM=/path/to/chrome`.

Tests and lint: `cd backend && uv run pytest && uv run ruff check .` · `cd frontend && pnpm lint`.

## Status

Walking skeleton: one Delhi service record (`data/schemes/`), deterministic eligibility, streamed chat
answers with citations, EN / हिंदी / Hinglish. The record is `partial`: fees and timelines show
"Verify locally" until a human checks the official sources (backlog S1-01, S1-03).

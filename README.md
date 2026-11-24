# Sahaay (सहाय)

An AI companion that helps people in Delhi go from confusion to action on government services:
**Discover · Qualify · Prepare · Navigate · Protect · Track.** Launch scope: income certificate,
SC/ST/OBC merit scholarship, old-age pension. English, हिंदी and Hinglish.

Sahaay is an AI assistant, not an official government channel. Eligibility, fees and dates come from
checked data files in `data/`, never from the model's memory. Anything not checked shows **"Verify
locally"**. Start with [CLAUDE.md](CLAUDE.md) for the rules and [docs/PROGRESS.md](docs/PROGRESS.md) for what is
done and what is left.

## What you can do in the app

| Page | What it does |
|---|---|
| `/chat` | Ask in any of the three languages. Get a service card with eligibility per rule (met / not met / unknown), fees, prerequisites and sources. |
| `/compare` | Compare 2 or 3 services side by side. |
| `/case` | Track your own progress through five steps you mark yourself, save the submission date and a masked reference number, download a case summary PDF. |
| `/documents` | Upload a photo or PDF (read in memory, never stored), correct what was read, confirm, and see which documents are ready or missing. |
| `/forms` | The official income certificate application with your details written on it. Review, tick "I checked every field", download. |
| `/drafts` | Complaint, RTI or grievance (CPGRAMS) draft as a PDF, English or Hindi, with the same review step. |
| `/privacy` | What is kept and never kept, everything saved about you, and "Delete my data". |

## Run locally

Needs Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20+ with pnpm, and for the full document and
PDF features: Tesseract with English and Hindi (`tesseract-ocr tesseract-ocr-hin`) and the Pango libraries
plus Noto fonts that WeasyPrint needs. Without them the app still runs; document reading and PDF
downloads report that they are unavailable, and the tests that need them are skipped.

```bash
# backend: http://localhost:8000
cd backend && uv sync && uv run fastapi dev app/main.py

# frontend: http://localhost:3000, in a second terminal
cd frontend && pnpm install && pnpm dev
```

With no keys at all the app runs on an offline stub model and an in-memory store, which is enough to try
every page. If `pnpm install` stops on "minimum release age", the lockfile has packages newer than your
pnpm's cooling-off window: wait a day or run `pnpm install --config.minimumReleaseAge=0`.

### Settings (two files, neither is committed)

| File | Holds | Read by |
|---|---|---|
| `.env` in the repo root (copy from `.env.example`) | `GEMINI_API_KEY`, `SUPABASE_URL` (full `https://<project>.supabase.co`), `SUPABASE_SECRET_KEY` | the backend |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | the browser bundle (public by design) |

Never put a key in `.env.example`: that file is committed. The secret key stays on the server only.

For the real database, run `supabase/migrations/0001_init.sql` then `0002_grants.sql` in the Supabase SQL editor
and enable **Anonymous sign-ins** (guest mode) under Authentication.

## Tests

```bash
cd backend && uv run pytest && uv run ruff check .        # unit and API tests, offline
cd backend && uv run python -m tests.eval.run              # small question set (stub or live model)
cd frontend && pnpm lint
cd frontend && pnpm exec playwright install chromium && pnpm e2e   # starts its own servers on 8100 and 3100
```

If Chromium is installed elsewhere, set `PW_CHROMIUM=/path/to/chrome`.

## Docker

Build from the repo root so `data/` is included. The backend image carries Tesseract (English and Hindi),
the PDF libraries and Noto fonts.

```bash
docker build -f backend/Dockerfile -t sahaay-backend .
docker run -p 8000:8000 --env-file .env -e CORS_ORIGINS='["https://your-frontend"]' sahaay-backend

docker build -f frontend/Dockerfile -t sahaay-frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://your-backend \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co \
  --build-arg NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_... .
docker run -p 3000:3000 sahaay-frontend
```

These Dockerfiles have not been built in CI yet; check the first build on your host.

## Demo script (5 minutes)

1. **Find and qualify.** `/chat`, tap "I am a student in Delhi, family income about 3 lakh". Show the card:
   unknowns are not "met", fees say "Verify locally" where the record has no figure, and every claim has a source.
   Confirm the facts with the chips and watch rules turn to Met.
2. **Compare.** `/compare`: income certificate against the scholarship.
3. **Prepare.** `/documents`: pick the pension, tap "I have this" on a document, or upload a test image.
   Then `/forms`: type a name and an Aadhaar number, press Review: only the last 4 digits show. Tick the box and download.
4. **Protect.** `/drafts`: write an RTI, review, download the PDF in Hindi.
5. **Track.** `/case`: mark the steps, enter a reference number (it is saved as XXXX + last 4), download the summary.
6. **Own your data.** `/privacy`: see what is saved, tick, "Delete my data".

## Known gaps

See [docs/PROGRESS.md](docs/PROGRESS.md). Main ones: the three service records are `partial` and still need a person to check
every field against the official pages; the glossary, screenshot assistant and email sign-in are not built; the
Postgres checkpointer, deploy and the native Hindi/Hinglish copy review are still to do.

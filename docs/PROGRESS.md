# Sahaay: progress against the backlog

Updated with each push. Status: **done** · **partly** · **todo** · **needs you** (human step).
PR #1 is merged into `main`; follow-up work goes in small PRs. Eval baseline: 17/17 (offline stub and live Gemini).

## Stage 0: Setup
| ID | Status | Notes |
|---|---|---|
| S0-01 repo structure | done | |
| S0-02 backend, /health, pytest, ruff | done | 92 tests |
| S0-03 frontend, next-intl en/hi/hn | done | language switch works |
| S0-04 design tokens + fonts | partly | tokens, fonts, Button done; no palette/type showcase page yet |
| S0-05 Supabase + Gemini keys | done | keys are in a private `.env`; rotate them later |
| S0-06 auth, migration, RLS | done | guest sign-in, JWT check, two-guest privacy test passed. Needs `0001` and `0002` SQL run (done) |
| S0-07 LLM wrapper | done | Gemini live; stub offline; budgets and rate limit tested with a fake provider |
| S0-08 PII masker | done | |

## Stage 1: Data and rules
| ID | Status | Notes |
|---|---|---|
| S1-01 scholarship + sources | done | Merit Scholarship SC/ST/OBC; `data/SOURCES.md` |
| S1-02 models, loader, allowlist check | done | |
| S1-03 three records verified | needs you | drafted from official pages, still `partial`; a person must check each field |
| S1-04 eligibility engine | done | includes conditional rules (`applies_if`) |
| S1-05 prerequisite chain + readiness | partly | chain shown on the card; cycle check in loader; readiness function waits for Stage 3 |
| S1-06 fee strip, freshness | done | |
| S1-07 `/services`, `/compare` | done | |

## Stage 2: Chat core
| ID | Status | Notes |
|---|---|---|
| S2-01 LangGraph skeleton | done | in-memory checkpointer |
| S2-02 understand (en/hi/hn) | done | live Gemini |
| S2-03 ask_missing | done | chips |
| S2-04 compose + guard | partly | templates, citations done; automated forbidden-claim scan on answers todo (eval checks it) |
| S2-05 `/chat` SSE, stop | done | |
| S2-06 chat UI | done | |
| S2-07 service card | partly | no alternatives list yet |
| S2-08 comparison page | done | 2 to 3 services, sources, EN/hi/hn, scrolls on phones |
| S2-09 home + app shell | partly | simple Home; no three-column desktop shell |
| S2-10 consent + save facts | done | tested in a browser |
| S2-11 report incorrect info | done | |
| S2-12 eval set | done | |
| S2-13 Playwright acceptance flow | done | 4 tests, offline (stub AI, no Supabase): `cd frontend && PW_CHROMIUM=<chrome path> pnpm e2e` |

## Stages 3 to 6
Not started: documents and OCR (3), forms and complaints (4), glossary, screenshots, journey, dashboard (5),
email sign-in, privacy page, Postgres checkpointer, Docker and deploy, README polish (6).
Delete-my-data already exists as an API (`DELETE /me/data`) and a link in chat.

## How to see the work
- Everything merged is on `main`: https://github.com/Krish-jain20/Sahaay-chatbot
- Run it: see README.md. Eval: `cd backend && uv run python -m tests.eval.run`.

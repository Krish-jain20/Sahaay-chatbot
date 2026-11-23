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
| S2-09 home + app shell | partly | phone and desktop shell done (nav 252px, chat, details panel 352px from 1200px wide); Home is still simple, no mockup-style hero yet |
| S2-10 consent + save facts | done | tested in a browser |
| S2-11 report incorrect info | done | |
| S2-12 eval set | done | |
| S2-13 Playwright acceptance flow | done | 6 tests, offline (stub AI, no Supabase): `cd frontend && PW_CHROMIUM=<chrome path> pnpm e2e` |

## Stage 3: Documents
| ID | Status | Notes |
|---|---|---|
| S3-01 | done | `POST /documents`, type and size checks, in memory; test proves nothing is written to disk |
| S3-02 | done | PDFs rendered with PyMuPDF; blur, resolution and blank-page checks (OpenCV) |
| S3-03 | done | Tesseract English+Hindi via stdin; extractors for income certificate, Aadhaar, PAN, passbook, marksheet; tested on synthetic documents only |
| S3-04 | done | IDs masked inside the extractors; tests check no full number in results, responses or logs |
| S3-05 | done | `POST /cases/{id}/documents` saves only user-confirmed fields, masked again server-side; upload never stored; checked on live Supabase |
| S3-06 | partly | readiness (missing / expired / too old) is built and tested, but the three records have no `validity_months` yet, so nothing shows "expired" until those are verified from sources (shows no guess) |
| S3-07 | done | document text is parsed by fixed patterns only and never reaches a model; injection fixture is inert |
| S3-08 | done | `/documents` page: pick service, upload or "I have this", review and edit fields, confirm, readiness bar. English, Hindi, Hinglish |

## Stages 4 to 6
Not started: forms and complaints (4), glossary, screenshots, journey, dashboard (5),
email sign-in, privacy page, Postgres checkpointer, Docker and deploy, README polish (6).
Delete-my-data already exists as an API (`DELETE /me/data`) and a link in chat.

## How to see the work
- Everything merged is on `main`: https://github.com/Krish-jain20/Sahaay-chatbot
- Run it: see README.md. Eval: `cd backend && uv run python -m tests.eval.run`.

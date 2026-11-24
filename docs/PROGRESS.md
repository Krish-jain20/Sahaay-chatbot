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

## Stage 4: Forms, complaints, summary
| ID | Status | Notes |
|---|---|---|
| S4-01 | done, needs a human look | official income certificate application, source https://revenue.delhi.gov.in/sites/default/files/revenue/cc/input_9055.pdf (linked from the Revenue Department income-certificate page, checked 2026-11-24), saved as `data/forms/delhi-income-certificate-application.pdf` with a checksum. It is a flat printed form, not fillable. The PDF header says both "Surviving Member Certificate" and "Income Certificate"; a person should confirm it is the form the e-District office wants. The old-age pension has no form PDF (online only), so it is not covered |
| S4-02 | done | PyMuPDF overlay fills the flat form (one digit per box for Aadhaar, mobile, PIN and date of birth); original PDF checksum is checked at startup; English letters and digits only |
| S4-03 | partly | field positions tested by reading the filled PDF back; a person should look at page 1 once. Page 1 only (beneficiary details and present address); income, assets, expenses and declaration are left for the applicant |
| S4-04 | done | `/drafts` and `/forms` pages: preview, then download only with the "I checked every field" tick and the hash of what was reviewed; any edit resets it |
| S4-05 | done | drafts mask identity numbers before preview and render; the form writes the Aadhaar number only onto the PDF in memory, previews show the last 4, and logs never hold it (tested); nothing is stored |
| S4-06 | needs you | grievance data per service (department, CPGRAMS, helpline) with sources; drafts leave office names to the user |
| S4-07 | todo | grievance vs RTI vs appeal explainer |
| S4-08 | done | complaint, RTI and CPGRAMS drafts as PDFs (WeasyPrint), English and Hindi; Hindi PDF embeds Noto Sans Devanagari; `/drafts` page in 3 languages |
| S4-09 | done | `GET /cases/{id}/summary.pdf?lang=en|hi`: services, own-progress steps, checklist with how each item was evaluated, fees as in the record ("Verify locally" when unknown), sources with date checked |
| S4-10 | partly | draft e2e tests added; flows 2 and 3 not written yet |

Needs the WeasyPrint system libraries (Pango) and Noto fonts; PDF tests skip where those are missing. The Dockerfile in S6-06 must include them.

## Stage 5: Navigate and track
| ID | Status | Notes |
|---|---|---|
| S5-01, S5-02 | todo | glossary needs sourced terms (human) |
| S5-03 | todo | screenshot assistant |
| S5-04 | done | `POST /cases/{id}/steps`, `DELETE /cases/{id}/steps/{n}`; user-recorded steps with timestamps; checked on live Supabase |
| S5-05 | done | five-step tracker on `/case`, labelled "Your own progress, not government status", with next-step guidance |
| S5-06 | partly | `/case` is the case page (tracker, readiness, shortcuts, summary PDF); a multi-case dashboard is not built yet |
| S5-07 | done | submission date and reference number; only `XXXX` + last 4 characters are stored or shown |

## Stage 6 and the rest
Not started: glossary and screenshots (5),
email sign-in, privacy page, Postgres checkpointer, Docker and deploy, README polish (6).
Delete-my-data already exists as an API (`DELETE /me/data`) and a link in chat.

## How to see the work
- Everything merged is on `main`: https://github.com/Krish-jain20/Sahaay-chatbot
- Run it: see README.md. Eval: `cd backend && uv run python -m tests.eval.run`.

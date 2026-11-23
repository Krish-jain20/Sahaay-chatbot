# Sahaay: Build Backlog

Work top to bottom. Do **one task at a time** ("Do S2-03"): plan, implement, test, commit. Feature IDs (D1, Q1, P4…) refer to `docs/PRD.md`.

**Stages are ordered so the app runs end to end after each one.** Never start a stage until the previous one works. If you must stop early, the last finished stage is a complete, demoable product. Stages 0–2 are the core; later stages add features in order of importance.

Legend: **[C]** Claude Code alone · **[H]** needs a human (data, decisions, keys) · **[C+H]** Claude drafts, human verifies.

---

## Stage 0: Setup

| ID | Task | Done when |
|---|---|---|
| S0-01 [C] | Repo: `backend/`, `frontend/`, `data/`, `docs/`; git; `.gitignore`; `.env.example` with the keys in ARCHITECTURE §13 | Structure matches CLAUDE.md |
| S0-02 [C] | Backend: FastAPI app, `/health`, config, ruff, pytest, uv | `uv run pytest` passes |
| S0-03 [C] | Frontend: Next.js + TS strict + Tailwind + shadcn/ui + `next-intl` (`en`, `hi`, `hn`) | `pnpm dev` runs; language switch changes a sample string |
| S0-04 [C] | Design tokens + fonts per `DESIGN.md` (`tokens.css`, Tailwind theme, `next/font`) | A page shows palette, type scale, buttons, focus ring |
| S0-05 [H] | Create Supabase project (enable anonymous sign-ins and email magic link), Gemini key; fill local `.env` | Keys work locally; nothing committed |
| S0-06 [C] | Supabase client on the frontend; JWT verification dependency in FastAPI; first migration (`profile_facts`, `cases`, `case_events`, `documents`, `submissions`, `corrections`, `usage`) with row-level security | Anonymous sign-in on load; an authenticated route returns the user id |
| S0-07 [C] | LLM wrapper `llm/client.py` with `extract`, `explain`, `vision`, `draft`; structured output; retries; masked-only logs; per-user rate limit and token budget | Unit tests with a fake provider; one live smoke call |
| S0-08 [C] | PII masker (Aadhaar with Verhoeff check, PAN, phone, bank account) | Table-driven tests including false positives |

## Stage 1: Data and rules

| ID | Task | Done when |
|---|---|---|
| S1-01 [H] | Choose the Delhi scholarship; list official source pages for all three services | URLs recorded in `data/SOURCES.md` |
| S1-02 [C] | Pydantic models + loader/validator from `DATA_SCHEMA.md`; `allowlist.json`; host-check validator | Invalid fixtures fail clearly |
| S1-03 [C+H] | Three service records drafted from the sources, then verified by a human | Records load; `status` set honestly; no invented values |
| S1-04 [C] | Eligibility engine: operators, per-rule MET/NOT_MET/UNKNOWN, overall verdict, exclusions, alternatives | Exhaustive unit tests; unknown never counts as met |
| S1-05 [C] | Prerequisite chain builder (acyclic check) and readiness checklist function | Tests for ordering, cycle rejection, missing/expired documents |
| S1-06 [C] | Fee strip builder (null → "Verify locally"); freshness check | Tests with null and stale fixtures |
| S1-07 [C] | `GET /services`, `GET /services/{id}`, `GET /compare` | Returns verified records with sources; compare payload for two services |

## Stage 2: Chat core (first demoable product)

| ID | Task | Done when |
|---|---|---|
| S2-01 [C] | LangGraph skeleton with `MemorySaver`: `understand`, `ask_missing`, `eligibility`, `compose` | Graph runs from a message to an answer payload in a test |
| S2-02 [C] | `understand`: intent + fact extraction in English/Hindi/Hinglish (structured output) | Fixture set classifies correctly; facts saved as unconfirmed |
| S2-03 [C] | `ask_missing`: 1–3 most useful unknown facts as chips/options | Asks only what can change the verdict |
| S2-04 [C] | `compose`: i18n templates, cards, citations, guard (every claim sourced; forbidden-claim scan); next-step selection from case state | Guard blocks a planted "approved" |
| S2-05 [C] | `POST /chat` SSE with `status`, `token`, `card`, `chips`, `citation`, `done`; `POST /chat/stop` | Streams events; Stop cancels |
| S2-06 [C] | Chat UI: bubbles, streaming, Stop, status pills, quick-reply chips, language switch | Matches the Chat mockup |
| S2-07 [C] | Service/eligibility card: verified badge, citation popover, met/unknown/not-met rows, exclusions, prerequisite chain, fee strip, alternatives | Matches the mockup; reduced-motion respected |
| S2-08 [C] | Scheme comparison page for 2–3 services | Table renders from the API; sources shown |
| S2-09 [C] | Home screen and app shell (mobile, and desktop three-column) | Matches the Home and full-desktop mockups |
| S2-10 [C] | Consent prompt before saving facts; profile facts save/confirm | Facts saved only after consent |
| S2-11 [C] | "Report incorrect information" button on every card → `corrections` | Submitting creates a row |
| S2-12 [C] | Eval set (English, Hindi, Hinglish, refusal, stale) + runner | Baseline score printed; CI-ready |
| S2-13 [C] | Playwright: acceptance flow 1 (find and qualify) | Passes |

**Checkpoint: Stage 2 is a complete product for Discover and Qualify.**

## Stage 3: Documents

| ID | Task | Done when |
|---|---|---|
| S3-01 [C] | Upload endpoint: type/size checks, in-memory processing, no file persistence | Test proves no file written to disk or DB |
| S3-02 [C] | PDF/image pipeline: PyMuPDF, OpenCV blur/resolution checks | Fixtures flagged correctly |
| S3-03 [C] | Tesseract `eng+hin` and extractors for income certificate, Aadhaar, PAN, bank passbook, marksheet | Good field accuracy on synthetic fixtures |
| S3-04 [C] | Mask Aadhaar/PAN/phone/account immediately after extraction | No full numbers in responses, DB or logs (tested) |
| S3-05 [C] | Confirm/edit extracted fields; persist only confirmed masked fields | Unconfirmed fields never feed rules |
| S3-06 [C] | Readiness checker wired into `documents` node: expired, missing, unreadable | Readable explanation per check; never says probability |
| S3-07 [C] | Prompt-injection guard for document text | Injection fixtures cannot trigger tools |
| S3-08 [C] | Document upload and readiness UI | Matches the Document check mockup |

## Stage 4: Forms, complaints, summary

| ID | Task | Done when |
|---|---|---|
| S4-01 [H] | Choose one official form (prefer fillable PDF); put it in `data/forms/` with source URL | File and `forms.json` entry exist |
| S4-02 [C] | Form engine: fillable via pypdf (flat via ReportLab overlay if needed) | Filled PDF opens correctly |
| S4-03 [C+H] | Field map and a visual snapshot test | Human approves the snapshot |
| S4-04 [C] | `prepare_draft` with confirm interrupt; review screen; "I checked every field" tick; `POST /chat/confirm` | Download blocked until confirmed |
| S4-05 [C] | Aadhaar/bank numbers handled at fill time in memory; only masked last 4 persisted | Tested: DB and logs never hold full numbers |
| S4-06 [C+H] | Grievance data per service (department, CPGRAMS, state channel, helpline) with sources | Fields filled and sourced |
| S4-07 [C] | Grievance guidance and the "grievance vs RTI vs appeal" explainer | Shown in chat and on the case page |
| S4-08 [C] | Complaint / RTI / CPGRAMS draft generator (user-confirmed facts only) rendered with WeasyPrint, Devanagari correct | PDF downloads; Hindi renders properly |
| S4-09 [C] | Case summary PDF (WeasyPrint) | PDF includes services, checklist, progress, sources |
| S4-10 [C] | Playwright: acceptance flows 2 and 3 | Pass |

**Checkpoint: Stage 4 covers Prepare and Protect.**

## Stage 5: Navigate and track

| ID | Task | Done when |
|---|---|---|
| S5-01 [C+H] | Glossary (`data/glossary.json`), 20+ terms with sources | Validator passes |
| S5-02 [C] | Terms explainer in chat via `explain` node; refuses if no match | Eval cases pass |
| S5-03 [C] | Screenshot assistant: upload, vision explanation, points to the user's confirmed document that holds the value; warns to hide personal details | Works on 3 sample screenshots; injection-safe |
| S5-04 [C] | Cases and journey API (user-recorded steps only) | Steps persisted with timestamps |
| S5-05 [C] | Journey tracker (5 steps) and step-by-step guidance from case state | Matches the mockup; labelled "your own progress" |
| S5-06 [C] | Dashboard and case folder pages (saved services, documents, drafts, next step) | Matches the Case folder mockup |
| S5-07 [C] | Reference number and submission date entry (masked reference) | Saved and shown in the case folder |

## Stage 6: Accounts, privacy, polish

| ID | Task | Done when |
|---|---|---|
| S6-01 [C] | Email magic-link sign-in; upgrading a guest keeps their data | Guest data present after sign-in |
| S6-02 [C] | Privacy page: view, edit, delete-my-data; privacy notice | Delete removes every row for the user |
| S6-03 [C] | Switch LangGraph to the Postgres checkpointer | A case resumes after a backend restart |
| S6-04 [C] | Safety tests: PII in logs and model payloads, injection, allowlist, forbidden claims | All pass |
| S6-05 [C] | Accessibility pass: keyboard path, aria-live for streaming, contrast, reduced motion | No serious axe issues on main screens |
| S6-06 [C] | Dockerfile (Tesseract + Hindi data, WeasyPrint deps, Noto fonts); deploy backend and frontend | Public URL works end to end |
| S6-07 [H] | Native Hindi/Hinglish copy review; final data check | Corrections applied |
| S6-08 [C] | README with setup, screenshots and a demo script | Another person can run the app |

## Optional extras (only after Stage 6)

Voice input and Listen button · scam checker · WhatsApp share · photo/signature resizer. All have mockups; none are in the final functionality list.

## Session prompts

- Start: "Read CLAUDE.md. Do S0-01 to S0-04. Plan first, show the plan, then implement."
- Per task: "Do S1-04. Follow `docs/DATA_SCHEMA.md` §3. Write tests. Stop when 'Done when' is true."
- Data: "Draft the `delhi-income-certificate` record from these official pages. Copy figures exactly; mark anything unconfirmed as null."
- Review: "Check Stage 3 for PII leaks into logs or model payloads; add tests for any gap."

Clear the session between tasks and commit after each one.

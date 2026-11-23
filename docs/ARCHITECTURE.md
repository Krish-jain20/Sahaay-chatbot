# Sahaay: Architecture (lean)

## 1. Principles

1. **Deterministic core, language shell.** Rules decide; the LLM understands language, explains, and drafts.
2. **Grounded or silent.** Facts come from `data/` with sources. No source, no claim.
3. **Simple first.** No vector search, no embeddings, no file storage, no extra services beyond Supabase.
4. **One LLM wrapper.** Everything model-related goes through `backend/app/llm/client.py`.
5. **Privacy by construction.** Mask PII at the boundary; process uploads in memory only.

## 2. Overview

```
Next.js app (en / hi / hn)
   chat · compare · case folder/dashboard · tools · privacy
        │  JSON + SSE   (Authorization: Supabase JWT)
        ▼
FastAPI
  ├─ api/      routes, JWT dependency, SSE, upload handling
  ├─ safety/   PII masker · link allowlist · injection guard · rate limit + token budget
  ├─ graph/    LangGraph: state, nodes, graph, checkpointer
  ├─ rules/    eligibility · prerequisites · readiness · fees   (pure Python)
  ├─ ocr/      Tesseract · OpenCV · PyMuPDF · field extractors
  ├─ pdf/      pypdf fill · ReportLab overlay · WeasyPrint documents
  └─ llm/      Gemini wrapper · prompts · budgets
        │
        ▼
Supabase Postgres (auth, users, facts, cases, events, corrections, checkpoints)
data/*.json   (loaded at startup, validated)
```

## 3. LangGraph (kept thin)

One graph, a fixed flow. Deterministic nodes are ordinary functions the graph calls. No autonomous tool-calling loops.

**State (`CaseState`):** `case_id`, `user_id`, `language`, `intent`, `facts` (profile facts with `confirmed` flag), `service_id`, `eligibility`, `prerequisites`, `documents` (masked extracted fields), `readiness`, `draft` (form or letter), `journey_step`, `pending_questions`, `answer` (cards, text keys, citations).

**Nodes**

| Node | What it does | LLM? |
|---|---|---|
| `understand` | Classify intent (find, info, compare, eligibility, documents, form, complaint, term, screenshot, other) and extract profile facts from the message | Yes: structured output, Flash-tier |
| `ask_missing` | Pick the 1–3 unknown facts that change the result; emit chips or options | No |
| `eligibility` | Run rules → met / not met / unknown per criterion, exclusions, alternatives, prerequisite chain, fee strip | No |
| `documents` | Readiness checklist from confirmed extracted fields (expired, missing, unreadable) | No |
| `prepare_draft` | Map confirmed facts to the form, or build complaint / RTI / CPGRAMS draft; **interrupt for user confirmation** before finalising | Draft only: stronger model |
| `explain` | Terms and screenshots: glossary lookup, vision for screenshots; refuses when no source | Yes |
| `compose` | Assemble answer: cards, text from i18n templates, citations, next step; run the guard (every claim has a source, no forbidden claims) | No |

**Flow:** `understand` → (`ask_missing` | `eligibility` | `documents` | `prepare_draft` | `explain`) → `compose` → end. `prepare_draft` pauses with a `confirm` event and resumes when the user confirms.

**Checkpointing:** start with `MemorySaver`; once the flow works, switch to the Postgres checkpointer (`langgraph-checkpoint-postgres`) using the Supabase connection string, keyed by `case_id`. If the graph gets complicated, simplify; do not add nodes for their own sake.

Text for answers comes from **i18n templates** filled with verified data, not from free LLM generation. This keeps Hindi/Hinglish answers consistent and cheap.

## 4. LLM wrapper (`llm/client.py`)

```python
class LLM:
    def extract(self, text: str, schema: type[BaseModel]) -> BaseModel      # Flash-tier, structured
    def explain(self, term_or_text: str, context: dict, lang: str) -> str    # glossary-grounded
    def vision(self, image: bytes, question: str, lang: str) -> VisionResult # screenshot assistant
    def draft(self, kind: str, facts: dict, lang: str) -> str                # complaint / RTI / CPGRAMS
```

Responsibilities: structured-output validation, retries, timeouts, masked-only request logging, per-user rate limit and daily token budget, and a clear error when the budget is exceeded. Uploaded text is passed only inside `<document>` delimiters with an instruction that it is data.

## 5. Data

- `data/*.json` loaded and validated at startup (see `DATA_SCHEMA.md`). Lookups are by `service_id`, jurisdiction and category. Comparison is a frontend table from the same records.
- `status: verified | partial`. Partial/stale fields render "Verify locally". `unverified` is never served.
- Add retrieval only if the record count grows well beyond the launch set.

## 6. Rules (`rules/`)

- **Eligibility:** per rule `MET | NOT_MET | UNKNOWN`; overall `LIKELY | NOT_ELIGIBLE | INCOMPLETE`. Any confirmed `NOT_MET` on a required rule → `NOT_ELIGIBLE` with the reason; any `UNKNOWN` required rule → `INCOMPLETE` and the fact is queued for `ask_missing`. Exclusions use the same operators and produce visible warnings.
- **Alternatives:** services in the same category whose required rules are not `NOT_MET`.
- **Prerequisites:** DAG from data, topologically ordered, with typical durations.
- **Readiness:** `completed_checks / total_checks` with each check listed and how it was evaluated. Never a probability.
- **Fees:** read from record; null → "Verify locally".

## 7. Documents (in memory only)

Upload → size/type check → PyMuPDF renders PDF pages → OpenCV quality (blur, resolution) → Tesseract `eng+hin` → per-document extractors (regex plus label proximity) → **PII masked immediately** → return extracted fields for the user to confirm → persist **only confirmed, masked fields** → discard the file and images. Findings: unreadable, expired (vs scheme `validity_months`/`issued_after`), missing required fields, missing required documents.

## 8. PDFs

- **Fill:** fillable form → `pypdf`; flat form → ReportLab overlay merged with `pypdf` (English/ASCII values; Hindi shaping is unreliable in ReportLab).
- **Generated documents** (case summary, complaint, RTI, CPGRAMS draft): HTML templates rendered with **WeasyPrint**, Noto Sans Devanagari embedded.
- Form flow: collect → review screen with every field editable → user ticks "I checked every field" → generate → return the file (not stored). Footer: "Prepared with Sahaay. Check before submission." Never auto-submit.

## 9. Auth and storage (Supabase)

- Guest mode = Supabase anonymous sign-in; email magic link upgrades the same user (link identity) so data is kept.
- FastAPI verifies the Supabase JWT on every route; user id from the token.
- Row-level security on all tables by `user_id`.

**Tables**

```
profile_facts(id, user_id, key, value, source, confirmed, updated_at)
cases(id, user_id, service_id, journey_step, state_json, created_at, updated_at)
case_events(id, case_id, step, note, at)              -- user-recorded progress only
documents(id, case_id, doc_type, fields_masked_json, issue_date, confirmed_at)   -- no files
submissions(id, case_id, reference_no_masked, submitted_on)
corrections(id, user_id, service_id, note, status, created_at)
usage(id, user_id, day, tokens_in, tokens_out)
```

Plus the LangGraph checkpoint tables. "Delete my data" removes every row for the user.

## 10. API

| Route | Purpose |
|---|---|
| `POST /chat` (SSE) | Send a message; stream events |
| `POST /chat/stop` | Cancel the running generation |
| `POST /chat/confirm` | Confirm or edit a pending draft (resumes the graph) |
| `GET /services`, `GET /services/{id}` | Verified records with sources |
| `GET /compare?ids=a,b` | Comparison payload |
| `POST /documents` | Upload; returns extracted masked fields and findings |
| `PATCH /documents/{id}/fields` | Confirm extracted fields |
| `GET /cases`, `GET /cases/{id}`, `PATCH /cases/{id}/step` | Dashboard, case folder, journey |
| `POST /drafts/form`, `POST /drafts/complaint` | Create draft (then confirm) |
| `GET /cases/{id}/summary.pdf` | Case summary |
| `POST /explain/term`, `POST /explain/screenshot` | Terms explainer, screenshot assistant |
| `POST /reports/incorrect` | Report incorrect information |
| `GET/PATCH/DELETE /me/data` | View, edit, delete everything |

**SSE events:** `status` (pill: id, label key, state) · `token` · `card` (service, eligibility, fee strip, comparison) · `chips` · `confirm` · `citation` · `error` · `done`.

## 11. Frontend

```
frontend/src/
  app/        /, /chat, /dashboard (case folder), /compare, /tools/screenshot, /privacy
  components/ ui/ · chat/ · cards/ · folder/ · tools/
  lib/        sse client, api, supabase client, i18n helpers
  messages/   en.json, hi.json, hn.json
  styles/     tokens.css (see DESIGN.md)
```

Layout and components follow `DESIGN.md` and the approved mockups.

## 12. Safety layer

| Control | Implementation |
|---|---|
| PII masking | Regex plus checksum (Aadhaar Verhoeff, PAN, phone, account); on input, before logs, before any model call; keep last 4 |
| Link allowlist | Exact host match against `data/allowlist.json` |
| Injection guard | Uploaded and screenshot text is delimited data; only the graph decides tool use; outputs validated against schemas |
| Guard in `compose` | Each claim has a source; blocks "approved", "verified document", "live status" |
| Rate/cost | Per-user rate limit and daily token budget in the wrapper |
| Consent | Facts saved only after the user agrees; revoke deletes them |

## 13. Configuration

`GEMINI_API_KEY`, `LLM_MODEL_FAST`, `LLM_MODEL_STRONG`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`, `DAILY_TOKEN_BUDGET`, `FRESHNESS_DAYS` (default 90). All in `.env.example`; never committed.

## 14. Deployment

Vercel (frontend), Docker on Render or Railway (backend, image includes Tesseract with Hindi data, WeasyPrint dependencies and Noto fonts), Supabase free tier.

## 15. Tests

- Unit: rules (exhaustive), PII masker, allowlist, extractors, date logic.
- Eval: a small set of Q&A in English, Hindi and Hinglish with required facts, required citations and forbidden claims.
- E2E (Playwright): the acceptance flows in the PRD.

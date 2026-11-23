# Sahaay: Product Requirements (final scope)

## 1. Vision

Sahaay is a personal AI companion for government services. A person describes their situation in simple English, Hindi or Hinglish; Sahaay finds what may apply, explains eligibility honestly, prepares documents and forms, explains the process in plain language, helps them raise complaints, and keeps their own progress organised.

**Core principle:** Sahaay is guided assistance, not an authority. It never guarantees eligibility, document authenticity or approval, and never presents user-recorded progress as live government status.

## 2. Launch scope

- **Region:** Delhi.
- **Services:** income certificate, one scholarship, old-age pension. Income certificate is a prerequisite for the scholarship.
- **Languages:** English, Hindi, Hinglish (all three are interface languages; replies follow the chosen language).
- **Accounts:** guest mode (anonymous) and email sign-in.
- **Channel:** responsive web app (mobile-first, three-column on desktop).

## 3. Functionalities (final list)

IDs are referenced by `docs/BACKLOG.md`.

### 1. Discover
| ID | Feature | Notes |
|---|---|---|
| D1 | **AI chatbot** | Simple English, Hindi or Hinglish; streaming replies with Stop; live status pills; quick-reply chips |
| D2 | **Scheme finder** | From age, income, occupation, location and situation described in chat; asks only the 1–3 most useful missing facts |
| D3 | **Scheme information** | Benefits, eligibility, documents, fees and application steps, each with a source |
| D4 | **Scheme comparison** | Two or three services side by side |

### 2. Qualify
| ID | Feature | Notes |
|---|---|---|
| Q1 | **Smart eligibility checker** | Per-criterion met / not met / unknown, deterministic |
| Q2 | **Eligibility explanation** | Why eligible or not, including exclusions |
| Q3 | **Alternative suggestions** | Other services from the data when not eligible |
| Q4 | **Prerequisite checker** | Which certificate or document is needed first, as an ordered chain |

### 3. Prepare
| ID | Feature | Notes |
|---|---|---|
| P1 | **Document upload** | Aadhaar, PAN, income certificate, and other supported types; processed in memory, not stored |
| P2 | **AI document scanner (OCR)** | Extract fields; user confirms them; Aadhaar/PAN masked immediately |
| P3 | **Application readiness checker** | Which requirements are complete or missing; checklist-based count, never an approval probability |
| P4 | **Automatic PDF form filling** | One supported official form; review screen, confirmation tick, then download |

### 4. Navigate
| ID | Feature | Notes |
|---|---|---|
| N1 | **Government terms explainer** | Plain-language explanation from a curated glossary |
| N2 | **Portal screenshot assistant** | Upload a screenshot; explain what a field needs; point to the user's confirmed document that holds the value |
| N3 | **Application journey tracker** | Five user-recorded steps: eligibility checked, documents prepared, form filled, application submitted, reference number saved |
| N4 | **Step-by-step guidance** | The single next action, derived from case state (not by the LLM) |

### 5. Protect
| ID | Feature | Notes |
|---|---|---|
| R1 | **Official fee checker** | Official fee, CSC maximum and processing time, from verified data |
| R2 | **Complaint generator** | Complaint, RTI and CPGRAMS drafts for user review |
| R3 | **Grievance guidance** | Where to complain: department, CPGRAMS, state channel, helpline; grievance vs RTI vs appeal explained |
| R4 | **Privacy protection** | Mask Aadhaar, PAN, phone, bank numbers; delete-my-data |

### 6. Track
| ID | Feature | Notes |
|---|---|---|
| T1 | **Personal dashboard** | Saved services, applications, documents, next steps |
| T2 | **Case folder** | Application information organised per service |
| T3 | **Case summary PDF** | Download a summary of progress |

### Platform
| ID | Feature | Notes |
|---|---|---|
| X1 | **Language support** | English, Hindi, Hinglish toggle, remembered |
| X2 | **Account access** | Guest mode and email sign-in; guest data can be kept by signing in |
| X3 | **Source citations and official links** | Citation chip on every fact; links only from the allowlist |
| X4 | **Report incorrect information** | Button on every card; stored for review |

### Optional extras (only after everything above works; they are in the mockups but not in the final list)
Voice input and Listen button · scam checker · WhatsApp share · photo/signature resizer.

### Not building now
Scheme change detection, CSC locator, family profiles, helper mode, SLA watchdog, reminders, notice decoder, what-if and benefit calculator, admin panel, additional states, official API integrations.

## 4. Behaviour requirements

1. **Grounded:** every fact traces to a record in `data/` with a source URL and `date_checked`. Missing or stale data shows "Verify locally".
2. **Deterministic core:** eligibility, prerequisites, readiness, fees and dates are Python functions. The LLM extracts facts from language, explains terms and screenshots, and drafts complaints; it does not decide.
3. **Honest limits:** no claim of authenticity, approval or live status.
4. **Confirmation:** the user confirms extracted fields, eligibility inputs, forms and drafts before use.
5. **Consent and control:** facts are saved with consent; the user can view, edit and delete everything.
6. **Safe links:** only exact-match allowlisted hosts appear as official.
7. **Simple language:** short sentences; Hindi and Hinglish are written naturally, not word-for-word translated.
8. **Accessible:** keyboard, screen reader labels, 44px targets, AA contrast, reduced motion.

## 5. Acceptance flows

1. **Find and qualify:** "I'm a student in Delhi, family income about 3 lakh" → asks for missing facts → shows scholarship and certificate with met/not met/unknown, exclusions, prerequisite chain, fee strip, sources → compare with another service.
2. **Prepare:** open the scholarship case → upload an income certificate → fields extracted and confirmed → readiness shows what is missing or expired → review pre-filled form → tick confirm → download PDF → journey tracker updates.
3. **Protect and follow up:** describe a delay or refusal → grievance guidance names the right channel → generate complaint/RTI draft → review → download.
4. **Understand:** paste a confusing term or upload a portal screenshot → plain explanation, pointing to the right document in the folder.
5. **Guest to account:** use as guest, sign in by email, data is kept; delete-my-data removes it.

## 6. Open items to resolve during the build

- Final scholarship and its official sources (S1-01).
- Which official form to support (must be a fillable PDF if possible) (S4-01).
- Retention: facts are kept until the user deletes them; uploads are never stored.

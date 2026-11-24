# Sahaay: Data Schema (lean)

All curated knowledge lives in `data/` as JSON, validated by Pydantic on load. **Never invent values.** If a fact is not verified, set it to `null`; the UI then shows "Verify locally".

## 1. Conventions

- IDs: lowercase kebab-case, stable (`delhi-income-certificate`).
- Dates ISO `YYYY-MM-DD`. Money as integer INR.
- User-facing strings: `{ "en": "...", "hi": "...", "hn": "..." }`. `hn` is Hinglish in Latin script. `en` required; missing `hi`/`hn` fall back to `en` and are flagged.
- Every fact points to a `source_ref` that exists in `sources[]`.
- `status`: `verified` (a human checked required fields against sources) · `partial` · `unverified` (never served).

## 2. Service record (`data/schemes/<id>.json`)

```jsonc
{
  "id": "delhi-income-certificate",
  "kind": "service",                       // "service" (certificate/procedure) | "scheme" (benefit)
  "status": "partial",
  "jurisdiction": { "level": "state", "state": "Delhi" },
  "name": { "en": "Income Certificate", "hi": "आय प्रमाण पत्र", "hn": "Aay Praman Patra" },
  "department": { "en": "[Department]" },
  "category": ["certificate"],             // scholarship | pension | certificate ...
  "summary": { "en": "[1–2 plain sentences]" },

  "benefit": { "amount_text": { "en": null }, "amount_inr": null, "frequency": null, "source_ref": "s1" },

  "eligibility": {
    "rules": [
      { "id": "r1", "field": "state_of_residence", "op": "eq", "value": "Delhi", "required": true,
        "label": { "en": "Resident of Delhi", "hi": "दिल्ली का निवासी", "hn": "Delhi ka nivasi" }, "source_ref": "s1" }
    ]
  },
  "exclusions": [
    { "id": "x1", "field": "receives_other_scholarship", "op": "is_true", "value": null,
      "label": { "en": "[Exclusion from source]" }, "source_ref": "s1" }
  ],

  "documents": [
    { "doc_type": "aadhaar", "required": true, "alternatives": ["voter_id"],
      "validity_months": null, "issued_after": null, "source_ref": "s1" }
  ],

  "prerequisites": [],                     // ids of other records; must be acyclic
  "typical_duration_days": { "min": null, "max": null, "source_ref": "s1" },

  "fees": { "official_online_inr": null, "csc_max_inr": null, "notes": { "en": null }, "source_ref": "s1" },
  "timeline": { "sla_days": null, "day_type": "working", "source_ref": "s1" },   // day_type null when the source does not say

  "apply": {
    "official_url": null,                  // host must be in allowlist.json
    "mode": ["online", "csc", "office"],
    "forms": ["delhi-income-certificate-form"],
    "steps": [ { "n": 1, "text": { "en": "[Step]" }, "source_ref": "s1" } ]
  },

  "grievance": {
    "channels": [ { "type": "cpgrams | state_portal | department | helpline", "name": null, "url": null, "phone": null, "source_ref": "s1" } ],
    "appellate_authority": { "en": null, "source_ref": null }
  },

  "sources": [
    { "id": "s1", "title": "[title]", "url": "https://[allowlisted host]/...", "publisher": "[Dept]",
      "date_checked": "2026-11-24", "effective_date": null }
  ],

  "verification": { "verified_by": null, "verified_on": null, "notes": null }
}
```

### Validation on load

1. `id` matches filename and is unique.
2. Every `source_ref` resolves to a `sources[].id`.
3. `apply.official_url` and every `sources[].url` host is in `allowlist.json`.
4. `prerequisites` form a DAG; ids exist.
5. `status: verified` requires `verification.verified_by`/`verified_on`, at least one source with `date_checked`, `apply.official_url`, and explicit `fees` and `timeline` (or notes saying none).
6. Rule `field` must be a known profile key (section 4); `op` valid for its type.
7. `date_checked` older than `FRESHNESS_DAYS` marks the record stale at runtime.

### 2a. Directory service (`data/directory/<id>.json`)
Information-only card for Compare (no eligibility rules, so it can never say "you qualify"). Fields: `id` (= filename), `jurisdiction`, `name`, `department`, `summary` (localised), `category`, `aliases`, `benefit`, `fee`, `time` (each an `{text, source_ref}` or null), `who`, `documents`, `steps` (lists of `{text, source_ref}`), `apply_url`, `sources` (same shape as in service records, every one with `date_checked`), `notes`. Details may be English only (`hi` and `hn` null fall back to `en`). A fact that no official page states is left null and shown as "Verify locally". Hosts of every source and `apply_url` must be in the allowlist.

## 3. Rule operators

`eq, ne, lt, lte, gt, gte, between [min,max], in, not_in, exists, is_true, is_false, age_between [min,max]`.
Per rule result: `MET`, `NOT_MET`, `UNKNOWN` (fact missing or unconfirmed). Unknown never counts as met.

A rule may carry `applies_if: { field, op, value }`. When that condition is confirmed false the rule is skipped; when it is unknown the rule is `UNKNOWN`. Example: the OBC-only income limit of the merit scholarship.

## 4. Profile keys

| key | type |
|---|---|
| `full_name` | string |
| `date_of_birth` | date |
| `gender` | enum |
| `state_of_residence` | string |
| `district` | string |
| `annual_family_income_inr` | integer |
| `social_category` | `general, sc, st, obc, ews, other` |
| `occupation` | `student, farmer, salaried, self_employed, unemployed, retired, homemaker, other` |
| `education_level` | enum |
| `institution_type` | `government, private, other` |
| `has_disability` | bool |
| `receives_other_scholarship` | bool |
| `receives_pension` | bool |
| `has_bank_account_linked` | bool |
| `marital_status` | enum |
| `years_resident_in_state` | number |
| `age` | integer (when the user gives an age, not a date of birth) |
| `previous_year_marks_percent` | number |

Each fact stores `source` (`user_said`, `form_input`, `document_extracted`), `confirmed`, `updated_at`. Only confirmed facts produce `MET`/`NOT_MET`. Aadhaar, PAN, phone and bank account numbers are **not** profile keys; when a form needs them they are entered at fill time, kept in memory for that request, and only the masked last 4 may be persisted.

## 5. Document types (`data/doc_types.json`)

```jsonc
{ "id": "income_certificate",
  "name": { "en": "Income Certificate", "hi": "आय प्रमाण पत्र" },
  "extract_fields": ["holder_name", "annual_income_inr", "issue_date", "issuing_authority"],
  "quality": { "min_dpi": 150, "max_blur_score_below": 100 } }
```

Starter set: `aadhaar` (masked only), `pan` (masked only), `income_certificate`, `age_proof`, `bank_passbook`, `marksheet`, `ration_card`, `passport_photo`.

## 6. Forms (`data/forms/forms.json`)

```jsonc
{ "id": "delhi-income-certificate-form",
  "title": "[Official form name]",
  "source_url": "https://[allowlisted host]/...pdf", "date_checked": "2026-11-24",
  "type": "fillable | flat",
  "file": "data/forms/<file>.pdf",
  "fields": [
    { "profile_key": "full_name", "pdf_field": "ApplicantName", "max_chars": 40 },
    { "profile_key": "date_of_birth", "page": 1, "x": 120, "y": 540, "font_size": 10, "format": "DD/MM/YYYY" }
  ],
  "requires_at_fill_time": ["aadhaar_last4"] }
```

For flat forms, `x`,`y` are PDF points from the bottom-left; use English/ASCII values.

## 7. Allowlist (`data/allowlist.json`)

```jsonc
{ "version": 1, "updated_on": "2026-11-24",
  "domains": [ { "host": "[official host]", "owner": "[Dept]", "verified_on": null } ] }
```

Exact hostname match (case-insensitive). Subdomains need their own entries. Entries need `verified_on`.

## 8. Glossary (`data/glossary.json`)

```jsonc
{ "id": "khatauni",
  "term": { "en": "Khatauni", "hi": "खतौनी", "hn": "Khatauni" },
  "aliases": ["khasra", "khatauni number"],
  "explanation": { "en": "[Plain explanation from the source]" },
  "where_to_find": { "en": "[e.g. on your land record copy]" },
  "maps_to_doc_type": "land_record", "maps_to_field": "khatauni_number",
  "source_ref": { "title": "[title]", "url": "https://[allowlisted host]/...", "date_checked": "2026-11-24" },
  "status": "partial" }
```

Terms are explained only from this file (plus screenshot context). Unknown term → "No verified explanation yet" with the report-incorrect-information option.

## 9. Eval set (`backend/tests/eval/eval_questions.json`)

```jsonc
{ "id": "q-001", "lang": "hn",
  "question": "income certificate ke liye kya documents chahiye?",
  "profile": { "state_of_residence": "Delhi" },
  "must_include": ["doc:aadhaar", "fee"], "must_cite": ["delhi-income-certificate"],
  "must_not_say": ["guaranteed", "approved", "live status"], "expect_refusal": false }
```

Include refusal cases (no source), stale-data cases and prompt-injection documents.

## 10. How records get made

1. Pick a service; gather the official pages/PDFs (URL and access date).
2. Draft the record as `unverified` (LLM-assisted extraction is fine; copy figures exactly from the source).
3. A human checks every required field against the source, fills `verification`, sets `status`.
4. The validator passes → the record is served. Add a few eval questions per record.

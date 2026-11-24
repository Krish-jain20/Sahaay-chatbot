import { API_URL } from "@/lib/sse";
import { getAccessToken } from "@/lib/supabase";
import type { WebCardData } from "@/lib/types";

async function authed(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
}

export interface SavedFact {
  key: string;
  value: unknown;
  confirmed: boolean;
}

export async function loadFacts(): Promise<Record<string, unknown>> {
  const res = await authed("/me/facts");
  if (!res.ok) return {};
  const rows = (await res.json()) as SavedFact[];
  return Object.fromEntries(rows.filter((r) => r.confirmed).map((r) => [r.key, r.value]));
}

export async function saveFacts(facts: Record<string, unknown>): Promise<boolean> {
  const results = await Promise.all(
    Object.entries(facts).map(([key, value]) =>
      authed("/me/facts", { method: "PUT", body: JSON.stringify({ key, value, source: "user_said", confirmed: true, consent: true }) }),
    ),
  );
  return results.every((r) => r.ok);
}

export async function deleteMyData(): Promise<boolean> {
  return (await authed("/me/data", { method: "DELETE" })).ok;
}

export async function reportIncorrect(serviceId: string, note: string): Promise<boolean> {
  return (await authed("/reports/incorrect", { method: "POST", body: JSON.stringify({ service_id: serviceId, note }) })).ok;
}

// ---- Cases and documents ----------------------------------------------------------------

export interface Check {
  doc_type: string;
  required: boolean;
  status: "ok" | "missing" | "expired" | "too_old";
  evaluated: "scanned_and_confirmed" | "user_declared" | "not_provided";
  issue_date: string | null;
  expires_on: string | null;
}
export interface Readiness {
  completed: number;
  total: number;
  checks: Check[];
}
export interface JourneyStep {
  n: number;
  key: string;
  done: boolean;
  done_at: string | null;
}
export interface Journey {
  steps: JourneyStep[];
  current: number | null;
  completed: number;
}
export interface Submission {
  reference_no_masked: string | null;
  submitted_on: string | null;
}
export interface CaseView {
  id: string;
  service_id: string;
  readiness: Readiness;
  journey: Journey;
  submission: Submission | null;
}
export interface DocTypeInfo {
  id: string;
  extract_fields: string[];
  required_fields: string[];
}
export interface ScanResult {
  doc_type: string;
  fields: Record<string, string | number | null>;
  findings: { code: string; field: string | null }[];
}

export async function openCase(serviceId: string): Promise<CaseView | null> {
  const created = await authed("/cases", { method: "POST", body: JSON.stringify({ service_id: serviceId }) });
  if (!created.ok) return null;
  const { id } = (await created.json()) as { id: string };
  const res = await authed(`/cases/${id}`);
  return res.ok ? ((await res.json()) as CaseView) : null;
}

export async function loadDocTypes(): Promise<DocTypeInfo[]> {
  const res = await authed("/doc-types");
  return res.ok ? ((await res.json()) as DocTypeInfo[]) : [];
}

/** Upload for reading only. The backend processes it in memory and returns masked fields. */
export async function scanDocument(file: File, docType: string): Promise<ScanResult | { error: string }> {
  const token = await getAccessToken();
  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);
  const res = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (res.ok) return (await res.json()) as ScanResult;
  const body = (await res.json().catch(() => ({}))) as { detail?: string };
  return { error: body.detail ?? "other" };
}

export async function saveDocument(
  caseId: string,
  docType: string,
  fields: Record<string, string | number | null>,
  selfDeclared: boolean,
): Promise<Readiness | null> {
  const res = await authed(`/cases/${caseId}/documents`, {
    method: "POST",
    body: JSON.stringify({ doc_type: docType, fields, self_declared: selfDeclared }),
  });
  return res.ok ? ((await res.json()) as { readiness: Readiness }).readiness : null;
}

// ---- Drafts (complaint / RTI / CPGRAMS) -------------------------------------------------

export type DraftKind = "complaint" | "rti" | "cpgrams";
export type DraftFields = Record<string, string | boolean>;
export interface DraftPreview {
  rows: { key: string; label: string; value: string }[];
  hash: string;
}

export async function previewDraft(
  kind: DraftKind,
  lang: string,
  fields: DraftFields,
): Promise<DraftPreview | { error: string }> {
  const res = await authed("/drafts/preview", { method: "POST", body: JSON.stringify({ kind, lang, fields }) });
  if (res.ok) return (await res.json()) as DraftPreview;
  const body = (await res.json().catch(() => ({}))) as { detail?: string };
  return { error: typeof body.detail === "string" ? body.detail : "failed" };
}

export async function downloadDraft(
  kind: DraftKind,
  lang: string,
  fields: DraftFields,
  hash: string,
): Promise<Blob | { error: string }> {
  const res = await authed("/drafts/pdf", {
    method: "POST",
    body: JSON.stringify({ kind, lang, fields, confirmed_hash: hash, checked_all_fields: true }),
  });
  if (res.ok) return await res.blob();
  const body = (await res.json().catch(() => ({}))) as { detail?: string };
  return { error: typeof body.detail === "string" ? body.detail : "failed" };
}

// ---- Official forms --------------------------------------------------------------------

export interface FormInfo {
  id: string;
  title: string;
  source_url: string;
  date_checked: string;
  fields: { key: string; max_chars: number; sensitive: boolean }[];
}
export interface FormPreview {
  values: Record<string, string>;
  hash: string;
}

export async function loadForms(): Promise<FormInfo[]> {
  const res = await authed("/forms");
  return res.ok ? ((await res.json()) as FormInfo[]) : [];
}

async function formError(res: Response): Promise<{ error: string }> {
  const body = (await res.json().catch(() => ({}))) as { detail?: string };
  return { error: typeof body.detail === "string" ? body.detail : "failed" };
}

export async function previewForm(id: string, values: Record<string, string>): Promise<FormPreview | { error: string }> {
  const res = await authed(`/forms/${id}/preview`, { method: "POST", body: JSON.stringify({ values }) });
  return res.ok ? ((await res.json()) as FormPreview) : formError(res);
}

export async function downloadForm(id: string, values: Record<string, string>, hash: string): Promise<Blob | { error: string }> {
  const res = await authed(`/forms/${id}/pdf`, {
    method: "POST",
    body: JSON.stringify({ values, confirmed_hash: hash, checked_all_fields: true }),
  });
  return res.ok ? await res.blob() : formError(res);
}

// ---- Journey (steps the user records themselves) ----------------------------------------

export async function recordStep(
  caseId: string,
  step: number,
  extra: { submitted_on?: string; reference?: string } = {},
): Promise<{ journey: Journey; submission: Submission | null } | { error: string }> {
  const res = await authed(`/cases/${caseId}/steps`, { method: "POST", body: JSON.stringify({ step, ...extra }) });
  return res.ok ? await res.json() : formError(res);
}

export async function undoStep(caseId: string, step: number): Promise<{ journey: Journey; submission: Submission | null } | null> {
  const res = await authed(`/cases/${caseId}/steps/${step}`, { method: "DELETE" });
  return res.ok ? await res.json() : null;
}

export async function downloadSummary(caseId: string, lang: string): Promise<Blob | null> {
  const res = await authed(`/cases/${caseId}/summary.pdf?lang=${lang === "hi" ? "hi" : "en"}`);
  return res.ok ? await res.blob() : null;
}

// ---- Privacy: what is stored ------------------------------------------------------------

export interface MyData {
  facts: { key: string; value: unknown; confirmed: boolean }[];
  cases: {
    id: string;
    service_id: string;
    documents: { doc_type: string; issue_date: string | null }[];
    steps: { step: number }[];
    submission: { reference_no_masked: string | null; submitted_on: string | null } | null;
  }[];
}

export async function loadMyData(): Promise<MyData | null> {
  const res = await authed("/me/data");
  return res.ok ? ((await res.json()) as MyData) : null;
}

export interface HelpAnswer {
  answer: string | null;
  web: WebCardData | null;
  matches: string[];
  /** web: live search; cards: matching cards plus general guidance; card_text: the best card's own text. */
  basis: "web" | "cards" | "card_text" | "none";
}

/** Ask the help page a free question: a guarded web answer plus the ids of matching verified cards. */
export async function askHelp(question: string, language: string): Promise<HelpAnswer | null> {
  const res = await authed("/help/ask", { method: "POST", body: JSON.stringify({ question, language }) });
  return res.ok ? ((await res.json()) as HelpAnswer) : null;
}

export interface HelpExplanation {
  text: string;
  web: WebCardData | null;
  basis: "web" | "card";
}

/** Explain a card, or with a situation, answer it from the card plus a web lookup. Null if unavailable. */
export async function explainHelpCard(cardId: string, language: string, situation: string): Promise<HelpExplanation | null> {
  const res = await authed("/help/explain", { method: "POST", body: JSON.stringify({ card_id: cardId, language, situation }) });
  return res.ok ? ((await res.json()) as HelpExplanation) : null;
}

export interface WebColumn {
  name: string;
  summary: string;
  web: WebCardData;
}

/** One unverified, web-found column for Compare. Resolves to a reason string when there is none. */
export async function compareWeb(query: string, language: string): Promise<WebColumn | "unavailable" | "none"> {
  const res = await authed("/compare/web", { method: "POST", body: JSON.stringify({ query, language }) });
  if (res.ok) return (await res.json()) as WebColumn;
  return res.status === 404 ? "none" : "unavailable";
}

// ---- Any uploaded form -----------------------------------------------------------------

export interface AnyFormField {
  id: string;
  label: string;
  mapped_profile_key: string | null;
  page: number;
  required: boolean;
  kind: "text" | "checkbox";
  sensitive: boolean;
  value?: string;
  label_i18n?: { en: string; hi: string; hn: string };
}

export interface AnyFormAnalysis {
  kind: "fillable" | "flat";
  pages: number;
  fields: Record<string, unknown>[];
  prefilled_fields: AnyFormField[];
  missing_fields: AnyFormField[];
  questions: { id: string; en: string; hi: string; hn: string }[];
  sensitive_keys: string[];
}

async function tokenHeader(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Upload a blank form. The browser sets the multipart boundary, so no Content-Type here. */
export async function analyzeForm(
  file: File,
  known: Record<string, string>,
  language: string,
): Promise<AnyFormAnalysis | { error: string }> {
  const body = new FormData();
  body.append("file", file);
  body.append("known", JSON.stringify(known));
  body.append("language", language);
  try {
    const res = await fetch(`${API_URL}/forms/analyze`, { method: "POST", body, headers: await tokenHeader() });
    return res.ok ? ((await res.json()) as AnyFormAnalysis) : formError(res);
  } catch {
    return { error: "failed" };
  }
}

export async function renderForm(
  file: File,
  analysis: AnyFormAnalysis,
  values: Record<string, string>,
): Promise<Blob | { error: string }> {
  const body = new FormData();
  body.append("file", file);
  body.append("fields", JSON.stringify(analysis.fields));
  body.append("values", JSON.stringify(values));
  body.append("checked_all_fields", "true");
  try {
    const res = await fetch(`${API_URL}/forms/render`, { method: "POST", body, headers: await tokenHeader() });
    return res.ok ? await res.blob() : formError(res);
  } catch {
    return { error: "failed" };
  }
}

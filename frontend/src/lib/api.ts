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
export type NextAction =
  | "check_eligibility"
  | "add_documents"
  | "confirm_documents"
  | "fill_form"
  | "submit"
  | "save_reference"
  | "follow_up"
  | "wait"
  | "done";
export interface FollowUp {
  days: number | null;
  user_set: boolean;
  due_on: string | null;
  due: boolean;
  days_since_submitted: number | null;
  reply_received: boolean;
}
export interface CaseLinks {
  official_url: string | null;
  sources: { title: string; url: string; publisher: string; date_checked: string | null }[];
  forms: { id: string; title: string; source_url: string; date_checked: string }[];
  draft_kind: string;
  grievance: { type: string; name: string | null; url: string | null; phone: string | null }[];
}
export interface CaseNote {
  id: string;
  at: string;
  text: string;
}
export interface CaseTodo {
  id: string;
  text: string;
  done: boolean;
}
export type KeyDateKind = "deadline" | "appointment" | "other";
/** A date the user set themselves (last date, appointment). Their own reminder, not an official date. */
export interface KeyDate {
  on: string;
  kind: KeyDateKind;
  label: string;
  days_left: number;
  soon: boolean;
  passed: boolean;
}
export interface WebSource {
  title: string;
  url: string;
  official: boolean;
  kind?: "official" | "gov_unchecked" | "other";
}
/** A service the user added. Every detail is theirs (or an AI suggestion they accepted), never checked by Sahaay. */
export interface CustomDetails {
  label: "added_by_you";
  ai_suggested: boolean;
  portal_url: string | null;
  portal_official: boolean;
  documents: { id: string; name: string; have: boolean }[];
  timeline_days: number | null;
  sources: WebSource[];
  added_on: string | null;
}
/** One case as the My cases page shows it. Progress is the user's own record, never government status. */
export interface CaseCard {
  id: string;
  service_id: string;
  service_name: string | null;
  department: string | null;
  created_at: string | null;
  readiness: Readiness;
  journey: Journey;
  submission: Submission | null;
  overview: {
    next_action: NextAction;
    missing: string[];
    docs_ready: number;
    docs_total: number;
    steps_done: number;
    steps_total: number;
    follow_up: FollowUp;
  };
  notes: CaseNote[];
  todos: CaseTodo[];
  todos_done: number;
  key_date: KeyDate | null;
  custom: CustomDetails | null;
  steps_text: { n: number; text: string | null }[];
  prerequisites: { id: string; name: string | null }[];
  links: CaseLinks;
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

export async function loadCases(lang: string): Promise<CaseCard[] | null> {
  const res = await authed(`/cases/overview?lang=${lang}`);
  return res.ok ? ((await res.json()) as CaseCard[]) : null;
}

export async function loadCase(id: string, lang: string): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}?lang=${lang}`);
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

/** Start tracking a service. Safe to call twice: the backend returns the existing case. */
export async function startCase(serviceId: string): Promise<string | null> {
  const res = await authed("/cases", { method: "POST", body: JSON.stringify({ service_id: serviceId }) });
  return res.ok ? ((await res.json()) as { id: string }).id : null;
}

export async function patchCase(
  id: string,
  lang: string,
  body: {
    follow_up_days?: number;
    clear_follow_up?: boolean;
    reply_received?: boolean;
    key_date?: string;
    key_date_kind?: KeyDateKind;
    key_date_label?: string;
    clear_key_date?: boolean;
  },
): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}?lang=${lang}`, { method: "PATCH", body: JSON.stringify(body) });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

export async function addNote(id: string, lang: string, text: string): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}/notes?lang=${lang}`, { method: "POST", body: JSON.stringify({ text }) });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

export async function deleteNote(id: string, lang: string, noteId: string): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}/notes/${noteId}?lang=${lang}`, { method: "DELETE" });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

export interface CustomServiceInput {
  name: string;
  department: string;
  portal_url: string | null;
  documents: string[];
  steps: string[];
  timeline_days: number | null;
  ai_suggested: boolean;
  sources: { title: string; url: string }[];
}

export async function addCustomCase(lang: string, body: CustomServiceInput): Promise<CaseCard | { error: string }> {
  const res = await authed(`/cases/custom?lang=${lang}`, { method: "POST", body: JSON.stringify(body) });
  return res.ok ? ((await res.json()) as CaseCard) : formError(res);
}

export async function editCustomCase(id: string, lang: string, body: CustomServiceInput): Promise<CaseCard | { error: string }> {
  const res = await authed(`/cases/${id}/custom?lang=${lang}`, { method: "PUT", body: JSON.stringify(body) });
  return res.ok ? ((await res.json()) as CaseCard) : formError(res);
}

export async function tickCustomDocument(id: string, lang: string, docId: string, have: boolean): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}/custom/documents/${docId}?lang=${lang}`, { method: "PATCH", body: JSON.stringify({ have }) });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

/** AI-suggested starting checklist for a service the user named. Unverified: shown labelled and editable. */
export interface ServiceSuggestion {
  found: boolean;
  department?: string;
  documents?: string[];
  steps?: string[];
  timeline_days?: number | null;
  note?: string;
  portal_url?: string | null;
  retrieved_on?: string;
  sources?: WebSource[];
}

export async function suggestService(name: string, lang: string): Promise<ServiceSuggestion | "unavailable"> {
  const res = await authed("/cases/suggest", { method: "POST", body: JSON.stringify({ name, lang }) });
  return res.ok ? ((await res.json()) as ServiceSuggestion) : "unavailable";
}

export async function addTodo(id: string, lang: string, text: string): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}/todos?lang=${lang}`, { method: "POST", body: JSON.stringify({ text }) });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

export async function tickTodo(id: string, lang: string, todoId: string, done: boolean): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}/todos/${todoId}?lang=${lang}`, { method: "PATCH", body: JSON.stringify({ done }) });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

export async function deleteTodo(id: string, lang: string, todoId: string): Promise<CaseCard | null> {
  const res = await authed(`/cases/${id}/todos/${todoId}?lang=${lang}`, { method: "DELETE" });
  return res.ok ? ((await res.json()) as CaseCard) : null;
}

export async function deleteCase(id: string): Promise<boolean> {
  return (await authed(`/cases/${id}`, { method: "DELETE" })).ok;
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

export interface DocRowData {
  doc_type: string;
  held: { doc_type: string; evaluated: Check["evaluated"]; issue_date: string | null } | null;
  needed_by: { case_id: string; name: string | null; required: boolean; status: Check["status"]; expires_on: string | null }[];
  scannable: boolean;
  required_anywhere: boolean;
  needs_attention: boolean;
}
export interface DocumentsOverview {
  documents: DocRowData[];
  missing_count: number;
  custom: { case_id: string; name: string; documents: { id: string; name: string; have: boolean }[] }[];
}

/** One list of documents across all cases: add once, it counts for every case that needs it. */
export async function loadDocumentsOverview(lang: string): Promise<DocumentsOverview | null> {
  const res = await authed(`/documents/overview?lang=${lang}`);
  return res.ok ? ((await res.json()) as DocumentsOverview) : null;
}

export async function serviceReadiness(serviceId: string): Promise<Readiness | null> {
  const res = await authed(`/services/${serviceId}/readiness`);
  return res.ok ? ((await res.json()) as Readiness) : null;
}

export async function removeDocument(docType: string): Promise<boolean> {
  return (await authed(`/documents/${docType}`, { method: "DELETE" })).ok;
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

// ---- Drafts (complaints, RTI, appeals, grievances) --------------------------------------

export type DraftKind = string;
export type DraftFields = Record<string, string | boolean>;
export interface DraftPreview {
  rows: { key: string; label: string; value: string }[];
  hash: string;
}
export interface DraftFieldDef {
  key: string;
  type: "text" | "multiline" | "date" | "checkbox" | "choice";
  required: boolean;
  label: string;
  hint: string | null;
  options: { id: string; label: string }[];
}
export interface DraftCard {
  id: DraftKind;
  group: string;
  icon: string;
  title: string;
  blurb: string;
  tags: string[];
  enclose: string | null;
  portal: { host: string; url: string; date_checked: string | null } | null;
  fields: DraftFieldDef[];
}
export interface DraftCatalog {
  groups: { id: string; title: string }[];
  kinds: DraftCard[];
}

export async function fetchDraftCatalog(lang: string): Promise<DraftCatalog | null> {
  try {
    const res = await fetch(`${API_URL}/drafts/catalog?lang=${lang}`);
    return res.ok ? ((await res.json()) as DraftCatalog) : null;
  } catch {
    return null;
  }
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

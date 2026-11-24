"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { AlertIcon, LinkIcon, SearchIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  addCustomCase,
  editCustomCase,
  suggestService,
  type CaseCard,
  type CustomServiceInput,
  type WebSource,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px]";
const labelCls = "mb-1 block text-[14px] font-semibold text-ink-2";
type Tr = (key: string, values?: Record<string, string | number>) => string;

const lines = (s: string) =>
  s
    .split("\n")
    .map((x) => x.trim())
    .filter(Boolean);

/**
 * Add (or edit) a service Sahaay has no verified record for. The user types the details; an optional AI
 * suggestion from a web search can prefill them, always labelled "not checked by Sahaay" and editable.
 */
export function AddService({
  existing,
  onSaved,
  onCancel,
}: {
  existing?: CaseCard;
  onSaved: (card: CaseCard) => void;
  onCancel: () => void;
}) {
  const t = useTranslations("case");
  const tt = t as unknown as Tr;
  const locale = useLocale();
  const c = existing?.custom;
  const [name, setName] = useState(existing?.service_name ?? "");
  const [dept, setDept] = useState(existing?.department ?? "");
  const [portal, setPortal] = useState(c?.portal_url ?? "");
  const [docs, setDocs] = useState(c ? c.documents.map((d) => d.name).join("\n") : "");
  const [steps, setSteps] = useState(existing ? existing.steps_text.map((s) => s.text ?? "").join("\n") : "");
  const [days, setDays] = useState(c?.timeline_days ? String(c.timeline_days) : "");
  const [ai, setAi] = useState(c?.ai_suggested ?? false);
  const [sources, setSources] = useState<WebSource[]>(c?.sources ?? []);
  const [retrieved, setRetrieved] = useState<string | null>(null);
  const [aiNote, setAiNote] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSuggest() {
    if (name.trim().length < 2) return setError(t("nameRequired"));
    setError(null);
    setInfo(null);
    setSuggesting(true);
    const r = await suggestService(name.trim(), locale);
    setSuggesting(false);
    if (r === "unavailable") return setInfo(t("suggestOff"));
    if (!r.found) return setInfo(t("suggestNone"));
    // Fill only what the user has not typed yet: their own words always win.
    if (!dept.trim() && r.department) setDept(r.department);
    if (!docs.trim() && r.documents?.length) setDocs(r.documents.join("\n"));
    if (!steps.trim() && r.steps?.length) setSteps(r.steps.join("\n"));
    if (!days && r.timeline_days) setDays(String(r.timeline_days));
    if (!portal.trim() && r.portal_url) setPortal(r.portal_url);
    setSources(r.sources ?? []);
    setRetrieved(r.retrieved_on ?? null);
    setAiNote(r.note ?? "");
    setAi(true);
  }

  async function onSave() {
    if (name.trim().length < 2) return setError(t("nameRequired"));
    if (portal.trim() && !/^https?:\/\/\S+$/.test(portal.trim())) return setError(t("badLink"));
    setError(null);
    setBusy(true);
    const body: CustomServiceInput = {
      name: name.trim(),
      department: dept.trim(),
      portal_url: portal.trim() || null,
      documents: lines(docs).slice(0, 20),
      steps: lines(steps).slice(0, 12),
      timeline_days: days ? Math.min(365, Math.max(1, Number(days))) : null,
      ai_suggested: ai,
      sources: sources.map((s) => ({ title: s.title, url: s.url })),
    };
    const r = existing ? await editCustomCase(existing.id, locale, body) : await addCustomCase(locale, body);
    setBusy(false);
    if ("error" in r) return setError(r.error.startsWith("Link") ? t("badLink") : t("saveError"));
    onSaved(r);
  }

  return (
    <section aria-labelledby="add-h" className="rounded-[20px] border border-line bg-surface p-5" data-testid="add-service">
      <h2 id="add-h" className="font-display text-[22px] font-extrabold leading-tight">
        {existing ? t("editService") : t("addTitle")}
      </h2>
      {!existing && <p className="mt-1 text-[14.5px] text-ink-2">{t("addHelp")}</p>}

      <div className="mt-4 space-y-4">
        <div>
          <label htmlFor="cs-name" className={labelCls}>{t("fName")}</label>
          <div className="flex flex-wrap gap-2">
            <input id="cs-name" maxLength={80} className={cn(input, "min-w-0 flex-1 basis-60")} value={name} onChange={(e) => setName(e.target.value)} aria-describedby="cs-name-hint" />
            <Button type="button" variant="chip" disabled={suggesting || busy} onClick={onSuggest} data-testid="suggest">
              <SearchIcon />
              {suggesting ? t("suggesting") : t("suggest")}
            </Button>
          </div>
          <p id="cs-name-hint" className="mt-1 text-[13px] text-ink-3">{t("fNameHint")}</p>
          <p className="mt-1 text-[13px] text-ink-3">{t("suggestHelp")}</p>
        </div>

        {info && (
          <p role="status" className="rounded-xl bg-bg-sunken px-3 py-2 text-[14.5px] text-ink-2">{info}</p>
        )}

        {ai && (
          <div role="note" className="rounded-xl bg-warn-100 p-3 text-[14px] text-warn-700" data-testid="ai-label">
            <p className="flex items-start gap-2 font-semibold">
              <AlertIcon className="mt-0.5 size-4 shrink-0" />
              {t("aiLabel")}
            </p>
            {aiNote && <p className="mt-1">{aiNote}</p>}
            {sources.length > 0 && <SourceList sources={sources} heading={tt("aiSources", { date: retrieved ?? c?.added_on ?? "" })} />}
          </div>
        )}

        <div>
          <label htmlFor="cs-dept" className={labelCls}>{t("fDept")}</label>
          <input id="cs-dept" maxLength={100} className={input} value={dept} onChange={(e) => setDept(e.target.value)} />
        </div>
        <div>
          <label htmlFor="cs-docs" className={labelCls}>{t("fDocs")}</label>
          <textarea id="cs-docs" rows={4} className={cn(input, "py-2")} value={docs} onChange={(e) => setDocs(e.target.value)} />
        </div>
        <div>
          <label htmlFor="cs-steps" className={labelCls}>{t("fSteps")}</label>
          <textarea id="cs-steps" rows={4} className={cn(input, "py-2")} value={steps} onChange={(e) => setSteps(e.target.value)} />
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_12rem]">
          <div>
            <label htmlFor="cs-portal" className={labelCls}>{t("fPortal")}</label>
            <input id="cs-portal" type="url" inputMode="url" maxLength={300} placeholder="https://" className={input} value={portal} onChange={(e) => setPortal(e.target.value)} aria-describedby="cs-portal-hint" />
            <p id="cs-portal-hint" className="mt-1 text-[13px] text-ink-3">{t("fPortalHint")}</p>
          </div>
          <div>
            <label htmlFor="cs-days" className={labelCls}>{t("fDays")}</label>
            <input id="cs-days" inputMode="numeric" className={input} value={days} onChange={(e) => setDays(e.target.value.replace(/\D/g, "").slice(0, 3))} />
          </div>
        </div>
      </div>

      {error && (
        <p role="alert" className="mt-3 flex items-start gap-2 text-bad-700">
          <AlertIcon className="mt-0.5 size-5 shrink-0" />
          {error}
        </p>
      )}
      <div className="mt-5 flex flex-wrap gap-2">
        <Button type="button" disabled={busy} onClick={onSave} data-testid="save-service">
          {existing ? t("saveEdits") : t("saveService")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>{t("cancel")}</Button>
      </div>
    </section>
  );
}

/** Web pages behind an AI suggestion: official only on an exact allowlist host, otherwise labelled. */
export function SourceList({ sources, heading }: { sources: WebSource[]; heading: string }) {
  const t = useTranslations("case");
  return (
    <div className="mt-2">
      <p className="text-[12.5px] font-semibold uppercase tracking-[0.05em]">{heading}</p>
      <ul className="mt-1 space-y-1">
        {sources.map((s) => (
          <li key={s.url} className="flex flex-wrap items-center gap-x-2">
            <a className="inline-flex min-h-11 items-center gap-1 break-all text-teal-700 underline" href={s.url} target="_blank" rel="noopener noreferrer">
              <LinkIcon className="size-4 shrink-0" />
              {s.title || s.url}
            </a>
            <span className={cn("rounded-full px-2 py-0.5 text-[12px] font-semibold", s.official ? "bg-ok-100 text-ok-700" : "bg-surface text-ink-2")}>
              {s.official ? t("srcOfficial") : s.kind === "gov_unchecked" ? t("srcGov") : t("srcOther")}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

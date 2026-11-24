"use client";

import Link from "next/link";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { AlertIcon, ArrowRightIcon, CheckIcon, FolderIcon, ShieldCheckIcon, XIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  loadCases,
  loadDocTypes,
  loadDocumentsOverview,
  removeDocument,
  saveDocument,
  scanDocument,
  serviceReadiness,
  startCase,
  tickCustomDocument,
  type CaseCard,
  type DocRowData,
  type DocTypeInfo,
  type DocumentsOverview,
  type Readiness,
  type ScanResult,
} from "@/lib/api";
import { API_URL } from "@/lib/sse";
import { cn } from "@/lib/utils";

interface ServiceLite {
  id: string;
  name: { en: string | null; hi: string | null; hn: string | null };
}

type Draft = { docType: string; result: ScanResult } | null;

type Tr = (key: string, values?: Record<string, string | number>) => string;

/** Documents: one list across all of your cases. Add a document once and it counts everywhere it is needed. */
export function DocumentCheck() {
  const t = useTranslations("docs");
  const tt = t as unknown as Tr;
  const tc = useTranslations("case") as unknown as Tr;
  const locale = useLocale() as "en" | "hi" | "hn";
  const [services, setServices] = useState<ServiceLite[]>([]);
  const [overview, setOverview] = useState<DocumentsOverview | null>(null);
  const [cases, setCases] = useState<CaseCard[]>([]);
  const [docTypes, setDocTypes] = useState<DocTypeInfo[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [pick, setPick] = useState("");
  const [preview, setPreview] = useState<Readiness | null>(null);
  const [tracking, setTracking] = useState(false);

  const reload = useCallback(async () => {
    const [ov, cs] = await Promise.all([loadDocumentsOverview(locale), loadCases(locale)]);
    if (!ov || !cs) return setState("error");
    setOverview(ov);
    setCases(cs);
    setState("ready");
  }, [locale]);

  useEffect(() => {
    Promise.all([fetch(`${API_URL}/services`).then((r) => (r.ok ? r.json() : Promise.reject())), loadDocTypes()])
      .then(([list, types]: [ServiceLite[], DocTypeInfo[]]) => {
        setServices(list);
        setDocTypes(types);
        const wanted = new URLSearchParams(window.location.search).get("service");
        if (wanted && list.some((x) => x.id === wanted)) setPick(wanted);
      })
      .catch(() => setState("error"));
    void reload();
  }, [reload]);

  const tracked = new Set(cases.map((c) => c.service_id));
  const untracked = services.filter((x) => !tracked.has(x.id));

  useEffect(() => {
    setPreview(null);
    if (pick) void serviceReadiness(pick).then(setPreview);
  }, [pick, overview]);

  if (state === "loading") return <p className="text-ink-2">{t("loading")}</p>;
  if (state === "error" || !overview)
    return (
      <p role="alert" className="text-bad-700">
        {t("loadError")}
      </p>
    );

  const hasDocs = overview.documents.length > 0;

  return (
    <div className="space-y-8">
      {hasDocs ? (
        <section aria-labelledby="mydocs-h" className="space-y-3">
          <h2 id="mydocs-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("yourDocs")}
          </h2>
          <p className="text-[14.5px] text-ink-2">{t("yourDocsHelp")}</p>
          <section
            aria-label={t("yourDocs")}
            className={cn("rounded-2xl border p-4", overview.missing_count ? "border-line bg-surface" : "border-teal-700 bg-teal-100")}
            data-testid="docs-summary"
          >
            <p className="flex items-start gap-2 text-[17px] font-bold" data-testid="progress-text">
              {overview.missing_count ? <AlertIcon className="mt-0.5 size-5 shrink-0 text-warn-700" /> : <CheckIcon className="mt-0.5 size-5 shrink-0 text-teal-700" />}
              {overview.missing_count ? tt("attention", { n: overview.missing_count }) : t("allSet")}
            </p>
            <p className="mt-1 text-[13.5px] text-ink-3">{t("caption")}</p>
            {cases.length > 0 && (
              <ul className="mt-3 space-y-1" data-testid="docs-cases">
                {cases.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={`/case?case=${c.id}`}
                      className="flex min-h-11 items-center justify-between gap-3 rounded-xl px-2 text-[15px] hover:bg-bg-sunken"
                    >
                      <span>
                        <span className="font-semibold">{c.service_name}</span>
                        <span className="block text-[13.5px] text-ink-2">{tc(`na.${c.overview.next_action}`)}</span>
                      </span>
                      <ArrowRightIcon className="size-4 shrink-0 text-teal-700" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <ul className="space-y-3" data-testid="doc-list">
            {overview.documents.map((row) => (
              <DocRow key={row.doc_type} row={row} scannable={docTypes.find((d) => d.id === row.doc_type) ?? null} onChanged={reload} />
            ))}
          </ul>
        </section>
      ) : (
        cases.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-bg-sunken p-6">
            <span className="grid size-11 place-items-center rounded-xl bg-teal-100 text-teal-700">
              <FolderIcon className="size-6" />
            </span>
            <p className="mt-3 font-display text-[19px] font-bold">{t("emptyTitle")}</p>
            <p className="mt-1 text-ink-2">{t("emptyBody")}</p>
            <Button asChild className="mt-4">
              <Link href="/case">
                {t("goCases")}
                <ArrowRightIcon />
              </Link>
            </Button>
          </div>
        )
      )}

      {overview.custom.length > 0 && (
        <section aria-labelledby="custom-h" className="space-y-3">
          <h2 id="custom-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("customTitle")}
          </h2>
          <p className="text-[14.5px] text-ink-2">{t("customHelp")}</p>
          {overview.custom.map((c) => (
            <div key={c.case_id} className="rounded-2xl border border-line bg-surface p-4" data-testid="custom-docs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-[17px] font-bold">{c.name}</h3>
                <Button asChild variant="ghost">
                  <Link href={`/case?case=${c.case_id}`}>{t("manageCase")}</Link>
                </Button>
              </div>
              {c.documents.length === 0 ? (
                <p className="mt-2 text-[14.5px] text-ink-2">{t("noDocsListed")}</p>
              ) : (
                <ul className="mt-2 divide-y divide-line">
                  {c.documents.map((d) => (
                    <li key={d.id}>
                      <label className="flex min-h-11 cursor-pointer items-center gap-3 py-1 text-[15px]">
                        <input
                          type="checkbox"
                          className="size-5 shrink-0 accent-teal-700"
                          checked={d.have}
                          onChange={async (e) => {
                            await tickCustomDocument(c.case_id, locale, d.id, e.target.checked);
                            await reload();
                          }}
                        />
                        {d.name}
                        {d.have && <span className="text-[13px] text-ink-3"> · {t("declared")}</span>}
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>
      )}

      {untracked.length > 0 && (
        <section aria-labelledby="check-svc-h" className="space-y-3">
          <h2 id="check-svc-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("checkService")}
          </h2>
          <p className="text-[14.5px] text-ink-2">{t("checkHelp")}</p>
          <div>
            <label htmlFor="service" className="mb-1 block text-[14px] font-semibold text-ink-2">
              {t("service")}
            </label>
            <select
              id="service"
              value={pick}
              onChange={(e) => setPick(e.target.value)}
              className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-[15px] md:w-auto"
            >
              <option value="">{t("pickService")}</option>
              {untracked.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name[locale] ?? x.name.en ?? x.id}
                </option>
              ))}
            </select>
          </div>
          {pick && preview && (
            <div className="rounded-2xl border border-line bg-surface p-4" data-testid="service-preview">
              <p className="text-[17px] font-bold">{t("progress", { done: preview.completed, total: preview.total })}</p>
              <ul className="mt-2 divide-y divide-line">
                {preview.checks.map((c) => (
                  <li key={c.doc_type} className="flex items-center justify-between gap-3 py-2 text-[15px]">
                    <span>
                      {t(`types.${c.doc_type}` as never)}
                      {!c.required && <span className="text-ink-3"> · {t("optional")}</span>}
                    </span>
                    <StatusChip status={c.status} />
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[13.5px] text-ink-3">{t("trackToAdd")}</p>
              <Button
                className="mt-2"
                disabled={tracking}
                onClick={async () => {
                  setTracking(true);
                  const id = await startCase(pick);
                  setTracking(false);
                  if (!id) return setState("error");
                  setPick("");
                  await reload();
                }}
              >
                {t("trackAndOpen")}
              </Button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function StatusChip({ status }: { status: DocRowData["needed_by"][number]["status"] }) {
  const t = useTranslations("docs");
  const ok = status === "ok";
  return (
    <span
      className={cn(
        "inline-flex min-h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-[13.5px] font-semibold",
        ok ? "bg-teal-700/10 text-teal-700" : status === "missing" ? "bg-bg-sunken text-ink-2" : "bg-marigold-500 text-ink",
      )}
    >
      {ok ? <CheckIcon className="size-4" /> : status === "missing" ? <XIcon className="size-4" /> : <AlertIcon className="size-4" />}
      {t(status)}
    </span>
  );
}

function DocRow({
  row,
  scannable,
  onChanged,
}: {
  row: DocRowData;
  scannable: DocTypeInfo | null;
  onChanged: () => Promise<void>;
}) {
  const t = useTranslations("docs");
  const tt = t as unknown as Tr;
  const format = useFormatter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const label = t(`types.${row.doc_type}` as never);
  // Any case that needs this document can hold it: one copy counts for all of them.
  const caseId = row.needed_by[0].case_id;
  const held = row.held;
  const worst = row.needed_by.find((n) => n.status !== "ok")?.status ?? "ok";
  const status = held ? worst : "missing";
  const expires = row.needed_by.find((n) => n.expires_on)?.expires_on ?? null;

  async function onFile(file: File | undefined) {
    if (!file || !scannable) return;
    setBusy(true);
    setError(null);
    const res = await scanDocument(file, row.doc_type);
    setBusy(false);
    if ("error" in res) {
      const known = ["too_large", "unsupported_type", "corrupt_file", "encrypted_pdf", "ocr_unavailable", "unknown_doc_type"];
      setError(t(`err_${known.includes(res.error) ? res.error : "other"}` as never));
      return;
    }
    setDraft({ docType: row.doc_type, result: res });
  }

  async function declare() {
    setBusy(true);
    const r = await saveDocument(caseId, row.doc_type, {}, true);
    if (r) await onChanged();
    else setError(t("saveError"));
    setBusy(false);
  }

  async function remove() {
    setBusy(true);
    const ok = await removeDocument(held?.doc_type ?? row.doc_type);
    if (ok) await onChanged();
    else setError(t("saveError"));
    setConfirmRemove(false);
    setBusy(false);
  }

  return (
    <li className="rounded-2xl border border-line bg-surface p-4" data-testid={`doc-${row.doc_type}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-[17px] font-bold">{label}</h3>
          <p className="text-[13.5px] text-ink-3">{row.required_anywhere ? t("required") : t("optional")}</p>
        </div>
        <StatusChip status={status} />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13.5px]" aria-label={t("neededBy")}>
        <span className="text-ink-3">{t("neededBy")}:</span>
        {row.needed_by.map((n) => (
          <Link
            key={n.case_id}
            href={`/case?case=${n.case_id}`}
            className="inline-flex min-h-8 items-center rounded-full border border-line px-2.5 font-semibold text-teal-700 hover:border-teal-700"
          >
            {n.name}
            {held && n.status !== "ok" ? ` · ${t(n.status)}` : ""}
          </Link>
        ))}
      </div>

      {held && (
        <p className="mt-2 text-[13.5px] text-ink-2">
          {held.evaluated === "scanned_and_confirmed" ? t("scanned") : t("declared")}
          {held.issue_date && ` · ${t("issued", { date: format.dateTime(new Date(held.issue_date), { dateStyle: "medium" }) })}`}
          {expires && ` · ${t("expires", { date: format.dateTime(new Date(expires), { dateStyle: "medium" }) })}`}
        </p>
      )}

      {!draft && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {scannable && (
            <>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,application/pdf"
                className="sr-only"
                aria-label={`${t("choose")}: ${label}`}
                onChange={(e) => {
                  void onFile(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
              <Button variant="secondary" disabled={busy} onClick={() => fileRef.current?.click()}>
                {busy ? t("reading") : held ? t("replace") : t("scan")}
              </Button>
            </>
          )}
          {!held && (
            <Button variant="ghost" disabled={busy} onClick={declare}>
              {t("declare")}
            </Button>
          )}
          {held &&
            (confirmRemove ? (
              <span className="flex flex-wrap items-center gap-2" role="group" aria-label={t("remove")}>
                <span className="text-[14.5px] font-semibold">{t("removeAsk")}</span>
                <Button variant="secondary" disabled={busy} onClick={remove}>{t("removeYes")}</Button>
                <Button variant="ghost" onClick={() => setConfirmRemove(false)}>{t("removeNo")}</Button>
              </span>
            ) : (
              <Button variant="ghost" disabled={busy} onClick={() => setConfirmRemove(true)} aria-label={`${t("remove")}: ${label}`}>
                {t("remove")}
              </Button>
            ))}
        </div>
      )}
      {scannable && !draft && !held && (
        <p className="mt-2 flex items-start gap-2 text-[13px] text-ink-3">
          <ShieldCheckIcon className="mt-0.5 size-4 shrink-0" />
          {t("hide")}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-[14px] text-bad-700">
          {error}
        </p>
      )}

      {draft && (
        <ReviewForm
          draft={draft}
          info={scannable}
          onCancel={() => setDraft(null)}
          onConfirm={async (fields) => {
            const r = await saveDocument(caseId, draft.docType, fields, false);
            if (r) {
              await onChanged();
              setDraft(null);
              setError(null);
            } else setError(tt("saveError"));
          }}
        />
      )}
    </li>
  );
}

function ReviewForm({
  draft,
  info,
  onCancel,
  onConfirm,
}: {
  draft: NonNullable<Draft>;
  info: DocTypeInfo | null;
  onCancel: () => void;
  onConfirm: (fields: Record<string, string | number | null>) => Promise<void>;
}) {
  const t = useTranslations("docs");
  const tt = t as unknown as (key: string, values?: Record<string, string>) => string;
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries((info?.extract_fields ?? []).map((f) => [f, String(draft.result.fields[f] ?? "")])),
  );
  const [saving, setSaving] = useState(false);
  const required = info?.required_fields ?? [];
  const canSave = required.every((f) => values[f]?.trim());

  return (
    <form
      className="mt-4 space-y-3 rounded-xl bg-bg-sunken p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setSaving(true);
        const fields = Object.fromEntries(
          Object.entries(values)
            .filter(([, v]) => v.trim())
            .map(([k, v]) => [k, k === "annual_income_inr" || k === "percentage" ? Number(v) : v.trim()]),
        );
        await onConfirm(fields);
        setSaving(false);
      }}
    >
      <h3 className="text-[15px] font-bold">{t("review")}</h3>
      <p className="text-[13.5px] text-ink-2">{t("reviewHelp")}</p>
      {draft.result.findings.length > 0 && (
        <ul role="alert" className="space-y-1 text-[14px] text-ink">
          {draft.result.findings.map((f, i) => (
            <li key={i} className="flex items-start gap-2">
              <AlertIcon className="mt-0.5 size-4 shrink-0" />
              {tt(`find_${f.code}`, { field: f.field ? tt(`fields.${f.field}`) : "" })}
            </li>
          ))}
        </ul>
      )}
      {(info?.extract_fields ?? []).map((f) => (
        <div key={f}>
          <label htmlFor={`f-${f}`} className="mb-1 block text-[14px] font-semibold text-ink-2">
            {t(`fields.${f}` as never)}
          </label>
          <input
            id={`f-${f}`}
            value={values[f] ?? ""}
            onChange={(e) => setValues((v) => ({ ...v, [f]: e.target.value }))}
            className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-[15px]"
          />
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={!canSave || saving}>
          {t("confirm")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}

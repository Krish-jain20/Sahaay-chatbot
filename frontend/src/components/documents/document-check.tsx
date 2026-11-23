"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { AlertIcon, CheckIcon, ShieldCheckIcon, XIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  loadDocTypes,
  openCase,
  saveDocument,
  scanDocument,
  type Check,
  type DocTypeInfo,
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

export function DocumentCheck() {
  const t = useTranslations("docs");
  const locale = useLocale() as "en" | "hi" | "hn";
  const [services, setServices] = useState<ServiceLite[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [docTypes, setDocTypes] = useState<DocTypeInfo[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    Promise.all([fetch(`${API_URL}/services`).then((r) => (r.ok ? r.json() : Promise.reject())), loadDocTypes()])
      .then(([list, types]: [ServiceLite[], DocTypeInfo[]]) => {
        setServices(list);
        setDocTypes(types);
        setServiceId(list[0]?.id ?? "");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    if (!serviceId) return;
    setState("loading");
    setReadiness(null);
    openCase(serviceId).then((c) => {
      if (!c) return setState("error");
      setCaseId(c.id);
      setReadiness(c.readiness);
      setState("ready");
    });
  }, [serviceId]);

  return (
    <div className="space-y-5">
      <div>
        <label htmlFor="service" className="mb-1 block text-[14px] font-semibold text-ink-2">
          {t("service")}
        </label>
        <select
          id="service"
          value={serviceId}
          onChange={(e) => setServiceId(e.target.value)}
          className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-[15px] md:w-auto"
        >
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name[locale] ?? s.name.en ?? s.id}
            </option>
          ))}
        </select>
      </div>

      {state === "loading" && <p className="text-ink-2">{t("loading")}</p>}
      {state === "error" && (
        <p role="alert" className="text-bad-700">
          {t("loadError")}
        </p>
      )}

      {state === "ready" && readiness && caseId && (
        <>
          <Progress readiness={readiness} />
          <ul className="space-y-3">
            {readiness.checks.map((c) => (
              <DocRow
                key={c.doc_type}
                check={c}
                caseId={caseId}
                scannable={docTypes.find((d) => d.id === c.doc_type) ?? null}
                onReadiness={setReadiness}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function Progress({ readiness }: { readiness: Readiness }) {
  const t = useTranslations("docs");
  const pct = readiness.total ? Math.round((readiness.completed / readiness.total) * 100) : 0;
  return (
    <section aria-label={t("title")} className="rounded-2xl border border-line bg-surface p-4">
      <p className="text-[17px] font-bold" data-testid="progress-text">
        {t("progress", { done: readiness.completed, total: readiness.total })}
      </p>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={readiness.total}
        aria-valuenow={readiness.completed}
        aria-label={t("progress", { done: readiness.completed, total: readiness.total })}
        className="mt-3 h-3 overflow-hidden rounded-full bg-bg-sunken"
      >
        <div className="h-full rounded-full bg-teal-700 motion-safe:transition-[width]" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-[13.5px] text-ink-3">{t("caption")}</p>
    </section>
  );
}

function DocRow({
  check,
  caseId,
  scannable,
  onReadiness,
}: {
  check: Check;
  caseId: string;
  scannable: DocTypeInfo | null;
  onReadiness: (r: Readiness) => void;
}) {
  const t = useTranslations("docs");
  const format = useFormatter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(null);
  const label = t(`types.${check.doc_type}` as never);
  const ok = check.status === "ok";
  const statusText = t(check.status);

  async function onFile(file: File | undefined) {
    if (!file || !scannable) return;
    setBusy(true);
    setError(null);
    const res = await scanDocument(file, check.doc_type);
    setBusy(false);
    if ("error" in res) {
      const known = ["too_large", "unsupported_type", "corrupt_file", "encrypted_pdf", "ocr_unavailable", "unknown_doc_type"];
      setError(t(`err_${known.includes(res.error) ? res.error : "other"}` as never));
      return;
    }
    setDraft({ docType: check.doc_type, result: res });
  }

  async function declare() {
    setBusy(true);
    const r = await saveDocument(caseId, check.doc_type, {}, true);
    setBusy(false);
    if (r) onReadiness(r);
    else setError(t("saveError"));
  }

  return (
    <li className="rounded-2xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-[17px] font-bold">{label}</h2>
          <p className="text-[13.5px] text-ink-3">{check.required ? t("required") : t("optional")}</p>
        </div>
        <span
          className={cn(
            "inline-flex min-h-8 items-center gap-1.5 rounded-full px-3 text-[13.5px] font-semibold",
            ok ? "bg-teal-700/10 text-teal-700" : check.status === "missing" ? "bg-bg-sunken text-ink-2" : "bg-marigold-500 text-ink",
          )}
        >
          {ok ? <CheckIcon className="size-4" /> : check.status === "missing" ? <XIcon className="size-4" /> : <AlertIcon className="size-4" />}
          {statusText}
        </span>
      </div>

      {check.evaluated !== "not_provided" && (
        <p className="mt-2 text-[13.5px] text-ink-2">
          {check.evaluated === "scanned_and_confirmed" ? t("scanned") : t("declared")}
          {check.issue_date && ` · ${t("issued", { date: format.dateTime(new Date(check.issue_date), { dateStyle: "medium" }) })}`}
          {check.expires_on && ` · ${t("expires", { date: format.dateTime(new Date(check.expires_on), { dateStyle: "medium" }) })}`}
        </p>
      )}

      {!draft && (
        <div className="mt-3 flex flex-wrap gap-2">
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
                {busy ? t("reading") : check.evaluated === "not_provided" ? t("scan") : t("replace")}
              </Button>
            </>
          )}
          {check.evaluated === "not_provided" && (
            <Button variant="ghost" disabled={busy} onClick={declare}>
              {t("declare")}
            </Button>
          )}
        </div>
      )}
      {scannable && !draft && check.evaluated === "not_provided" && (
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
              onReadiness(r);
              setDraft(null);
              setError(null);
            } else setError(t("saveError"));
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

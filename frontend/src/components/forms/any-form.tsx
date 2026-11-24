"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { AlertIcon, ShieldCheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { analyzeForm, renderForm, type AnyFormAnalysis, type AnyFormField } from "@/lib/api";

const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px]";
const SENSITIVE = new Set(["aadhaar", "pan", "mobile", "bank_account"]);
const NUMERIC = new Set(["aadhaar", "mobile", "pin", "annual_income", "bank_account"]);
const SESSION_KEY = "sahaay.formProfile";
const MAX_MB = 8;

/** Facts typed earlier in this tab. Identity numbers are never kept, and the tab's storage ends with the tab. */
function knownFacts(): Record<string, string> {
  try {
    const raw = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? "{}") as Record<string, string>;
    return Object.fromEntries(Object.entries(raw).filter(([k, v]) => !SENSITIVE.has(k) && typeof v === "string"));
  } catch {
    return {};
  }
}

function rememberFacts(fields: AnyFormField[], values: Record<string, string>) {
  try {
    const next = knownFacts();
    for (const f of fields) {
      const k = f.mapped_profile_key;
      if (k && !SENSITIVE.has(k) && values[f.id]?.trim()) next[k] = values[f.id].trim();
    }
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
  } catch {
    /* storage can be blocked: the form still works */
  }
}

const maskValue = (v: string) => `XXXX ${v.replace(/\D/g, "").slice(-4) || "••••"}`;

export function AnyForm() {
  const t = useTranslations("forms.any");
  const tt = t as unknown as (key: string, values?: Record<string, string | number>) => string;
  const locale = useLocale() as "en" | "hi" | "hn";
  const fileRef = useRef<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [stage, setStage] = useState<"pick" | "finding" | "fill">("pick");
  const [analysis, setAnalysis] = useState<AnyFormAnalysis | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [reviewing, setReviewing] = useState(false);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const message = (code: string) => {
    const known = [
      "unsupported_type", "file_too_large", "image_too_large", "unreadable_file", "encrypted_pdf", "too_many_pages",
      "rotated_page", "no_fields_found", "vision_unavailable", "rate_limited", "invalid_aadhaar", "invalid_pan",
    ];
    return known.includes(code) ? tt(`err_${code}`) : t("err_failed");
  };

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    fileRef.current = f;
    setFileName(f?.name ?? "");
    setError(null);
  }

  async function onFind(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current;
    if (!file) return setError(t("err_choose"));
    if (file.size > MAX_MB * 1024 * 1024) return setError(t("err_file_too_large"));
    setError(null);
    setStage("finding");
    const res = await analyzeForm(file, knownFacts(), locale);
    if ("error" in res) {
      setStage("pick");
      return setError(message(res.error));
    }
    const initial: Record<string, string> = {};
    for (const f of res.prefilled_fields) initial[f.id] = f.value ?? "";
    setValues(initial);
    setAnalysis(res);
    setReviewing(false);
    setChecked(false);
    setStage("fill");
  }

  const set = (id: string, v: string) => {
    setValues((s) => ({ ...s, [id]: v }));
    setReviewing(false); // any edit voids the review and the tick
    setChecked(false);
  };

  function reset() {
    fileRef.current = null;
    setFileName("");
    setAnalysis(null);
    setValues({});
    setReviewing(false);
    setChecked(false);
    setError(null);
    setStage("pick");
  }

  async function onDownload() {
    const file = fileRef.current;
    if (!file || !analysis) return;
    setBusy(true);
    setError(null);
    const filled = Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim()));
    const res = await renderForm(file, analysis, filled);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    rememberFacts([...analysis.prefilled_fields, ...analysis.missing_fields], values);
    const url = URL.createObjectURL(res);
    const a = document.createElement("a");
    a.href = url;
    a.download = "filled-form.pdf";
    a.click();
    URL.revokeObjectURL(url);
  }

  const labelOf = (f: AnyFormField) => f.label_i18n?.[locale] ?? f.label;
  const control = (f: AnyFormField) => {
    const id = `any-${f.id}`;
    if (f.kind === "checkbox") {
      return (
        <label key={f.id} className="flex min-h-11 items-center gap-3 text-[15px]">
          <input
            type="checkbox"
            className="size-5"
            checked={values[f.id] === "yes"}
            onChange={(e) => set(f.id, e.target.checked ? "yes" : "")}
          />
          {labelOf(f)}
        </label>
      );
    }
    const key = f.mapped_profile_key ?? "";
    return (
      <div key={f.id}>
        <label htmlFor={id} className="mb-1 block text-[14px] font-semibold text-ink-2">
          {labelOf(f)}
          {f.required && <span className="font-normal text-ink-3"> ({t("required")})</span>}
        </label>
        <input
          id={id}
          className={input}
          maxLength={300}
          inputMode={NUMERIC.has(key) ? "numeric" : undefined}
          autoComplete="off"
          placeholder={key === "dob" ? "DD/MM/YYYY" : undefined}
          value={values[f.id] ?? ""}
          onChange={(e) => set(f.id, e.target.value)}
        />
      </div>
    );
  };

  if (stage !== "fill" || !analysis) {
    return (
      <form onSubmit={onFind} className="space-y-4" data-testid="any-form-upload">
        <p className="text-ink-2">{t("help")}</p>
        <p className="flex items-start gap-2 text-[13.5px] text-ink-3">
          <ShieldCheckIcon className="mt-0.5 size-4 shrink-0" />
          {t("privacy")}
        </p>
        <div>
          <label htmlFor="any-file" className="mb-1 block text-[15px] font-semibold">{t("choose")}</label>
          <input
            id="any-file"
            type="file"
            accept="application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg"
            onChange={onPick}
            className="block min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px] file:mr-3 file:min-h-9 file:rounded-full file:border-0 file:bg-teal-700 file:px-4 file:text-[14px] file:font-semibold file:text-white"
          />
          {fileName && <p className="mt-1 text-[13.5px] text-ink-3">{fileName}</p>}
        </div>
        <Button type="submit" disabled={stage === "finding"}>
          {stage === "finding" ? t("finding") : t("find")}
        </Button>
        {stage === "finding" && (
          <p role="status" className="text-ink-2" data-testid="any-form-loading">{t("findingLong")}</p>
        )}
        {error && (
          <p role="alert" className="flex items-start gap-2 text-bad-700">
            <AlertIcon className="mt-0.5 size-5 shrink-0" />
            {error}
          </p>
        )}
      </form>
    );
  }

  const all = [...analysis.prefilled_fields, ...analysis.missing_fields];
  const filledRows = all.filter((f) => values[f.id]?.trim());
  const show = (f: AnyFormField) => {
    const v = values[f.id].trim();
    if (f.kind === "checkbox") return t("ticked");
    return f.sensitive || (f.mapped_profile_key && SENSITIVE.has(f.mapped_profile_key)) ? maskValue(v) : v;
  };

  return (
    <div className="space-y-5" data-testid="any-form-fill">
      <p role="status" data-testid="any-form-summary" className="rounded-2xl border border-line bg-surface p-4 text-[15px]">
        {tt("found", { n: all.length, k: analysis.prefilled_fields.length, m: analysis.missing_fields.length })}
        <span className="block text-[13.5px] text-ink-3">{fileName}</span>
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          setReviewing(true);
        }}
        className="space-y-5"
      >
        {analysis.missing_fields.length > 0 ? (
          <fieldset className="space-y-4">
            <legend className="mb-1 text-[17px] font-bold">{t("fillRest")}</legend>
            {analysis.missing_fields.map(control)}
          </fieldset>
        ) : (
          <p className="text-ink-2">{t("noneMissing")}</p>
        )}
        {analysis.prefilled_fields.length > 0 && (
          <details className="rounded-2xl border border-line bg-surface p-4">
            <summary className="min-h-11 cursor-pointer text-[15px] font-semibold">
              {tt("alreadyFilled", { n: analysis.prefilled_fields.length })}
            </summary>
            <div className="mt-3 space-y-4">{analysis.prefilled_fields.map(control)}</div>
          </details>
        )}
        <div className="flex flex-wrap gap-3">
          <Button type="submit">{t("review")}</Button>
          <Button type="button" variant="secondary" onClick={reset}>{t("another")}</Button>
        </div>
      </form>

      {error && (
        <p role="alert" className="flex items-start gap-2 text-bad-700">
          <AlertIcon className="mt-0.5 size-5 shrink-0" />
          {error}
        </p>
      )}

      {reviewing && (
        <section aria-labelledby="any-review-h" className="space-y-3 rounded-2xl border border-line bg-surface p-4">
          <h2 id="any-review-h" className="text-[17px] font-bold">{t("reviewTitle")}</h2>
          <p className="text-[14px] text-ink-2">{t("reviewHelp")}</p>
          {filledRows.length === 0 ? (
            <p className="text-ink-2">{t("nothingFilled")}</p>
          ) : (
            <dl className="space-y-2" data-testid="any-form-review">
              {filledRows.map((f) => (
                <div key={f.id}>
                  <dt className="text-[13.5px] font-semibold text-ink-2">{labelOf(f)}</dt>
                  <dd className="text-[15px]">{show(f)}</dd>
                </div>
              ))}
            </dl>
          )}
          <p className="flex items-start gap-2 text-[13px] text-ink-3">
            <ShieldCheckIcon className="mt-0.5 size-4 shrink-0" />
            {t("sensitiveNote")}
          </p>
          <p className="rounded-xl bg-marigold-050 px-3 py-2 text-[13.5px] text-ink-2">{t("notice")}</p>
          <label className="flex min-h-11 items-center gap-3 text-[15px] font-semibold">
            <input type="checkbox" className="size-5" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
            {t("tick")}
          </label>
          <Button type="button" disabled={!checked || busy || filledRows.length === 0} onClick={onDownload}>
            {busy ? t("downloading") : t("download")}
          </Button>
        </section>
      )}
    </div>
  );
}

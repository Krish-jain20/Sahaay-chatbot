"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { AlertIcon, ShieldCheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { downloadDraft, previewDraft, type DraftFields, type DraftKind, type DraftPreview } from "@/lib/api";

interface Field {
  key: string;
  required: boolean;
  multiline?: boolean;
  checkbox?: boolean;
}

// Mirrors backend/app/pdf/drafts.py SPECS. The server is the source of truth and validates again.
const FIELDS: Record<DraftKind, Field[]> = {
  complaint: [
    { key: "full_name", required: true },
    { key: "address", required: false, multiline: true },
    { key: "addressed_to", required: true },
    { key: "service_name", required: true },
    { key: "application_ref", required: false },
    { key: "applied_on", required: false },
    { key: "issue", required: true, multiline: true },
    { key: "requested_action", required: true, multiline: true },
  ],
  rti: [
    { key: "full_name", required: true },
    { key: "address", required: true, multiline: true },
    { key: "authority", required: true },
    { key: "info_sought", required: true, multiline: true },
    { key: "period", required: false },
    { key: "bpl", required: false, checkbox: true },
  ],
  cpgrams: [
    { key: "full_name", required: true },
    { key: "contact", required: false },
    { key: "department", required: true },
    { key: "grievance", required: true, multiline: true },
    { key: "requested_action", required: true, multiline: true },
  ],
};

const KINDS: DraftKind[] = ["complaint", "rti", "cpgrams"];
const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px]";

export function DraftBuilder() {
  const t = useTranslations("drafts");
  const tt = t as unknown as (key: string, values?: Record<string, string>) => string;
  const locale = useLocale();
  const [kind, setKind] = useState<DraftKind>("complaint");
  const [lang, setLang] = useState<"en" | "hi">(locale === "hi" ? "hi" : "en");
  const [values, setValues] = useState<DraftFields>({});
  const [review, setReview] = useState<DraftPreview | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fields = FIELDS[kind];
  const set = (k: string, v: string | boolean) => {
    setValues((s) => ({ ...s, [k]: v }));
    // Any edit after review invalidates the review and the tick.
    setReview(null);
    setChecked(false);
  };

  function message(code: string): string {
    if (code.startsWith("missing_required:")) {
      const names = code.split(":")[1].split(",").map((k) => tt(`f_${k}`));
      return t("missing", { fields: names.join(", ") });
    }
    return code === "changed_since_review" ? t("changed") : t("failed");
  }

  async function onReview(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await previewDraft(kind, lang, values);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    setReview(res);
    setChecked(false);
  }

  async function onDownload() {
    if (!review) return;
    setBusy(true);
    setError(null);
    const res = await downloadDraft(kind, lang, values, review.hash);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    const url = URL.createObjectURL(res);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sahaay-${kind}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-5">
      <fieldset className="space-y-2">
        <legend className="mb-1 text-[14px] font-semibold text-ink-2">{t("kind")}</legend>
        <div className="flex flex-wrap gap-2">
          {KINDS.map((k) => (
            <Button
              key={k}
              type="button"
              variant={k === kind ? "primary" : "secondary"}
              aria-pressed={k === kind}
              onClick={() => {
                setKind(k);
                setValues({});
                setReview(null);
                setChecked(false);
                setError(null);
              }}
            >
              {tt(k)}
            </Button>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="draft-lang" className="mb-1 block text-[14px] font-semibold text-ink-2">
          {t("draftLang")}
        </label>
        <select
          id="draft-lang"
          value={lang}
          onChange={(e) => {
            setLang(e.target.value as "en" | "hi");
            setReview(null);
            setChecked(false);
          }}
          className="min-h-11 rounded-xl border border-line bg-surface px-3 text-[15px]"
        >
          <option value="en">{t("langEn")}</option>
          <option value="hi">{t("langHi")}</option>
        </select>
      </div>

      <form onSubmit={onReview} className="space-y-4">
        {fields.map((f) => (
          <div key={f.key}>
            {f.checkbox ? (
              <label className="flex min-h-11 items-center gap-3 text-[15px]">
                <input
                  type="checkbox"
                  className="size-5"
                  checked={values[f.key] === true}
                  onChange={(e) => set(f.key, e.target.checked)}
                />
                {tt(`f_${f.key}`)}
              </label>
            ) : (
              <>
                <label htmlFor={`d-${f.key}`} className="mb-1 block text-[14px] font-semibold text-ink-2">
                  {tt(`f_${f.key}`)}
                  {!f.required && <span className="font-normal text-ink-3"> ({t("optional")})</span>}
                </label>
                {f.multiline ? (
                  <textarea
                    id={`d-${f.key}`}
                    rows={4}
                    className={input}
                    value={(values[f.key] as string) ?? ""}
                    onChange={(e) => set(f.key, e.target.value)}
                  />
                ) : (
                  <input
                    id={`d-${f.key}`}
                    className={input}
                    value={(values[f.key] as string) ?? ""}
                    onChange={(e) => set(f.key, e.target.value)}
                  />
                )}
              </>
            )}
          </div>
        ))}
        <p className="flex items-start gap-2 text-[13px] text-ink-3">
          <ShieldCheckIcon className="mt-0.5 size-4 shrink-0" />
          {t("hide")}
        </p>
        <Button type="submit" disabled={busy}>
          {t("preview")}
        </Button>
      </form>

      {error && (
        <p role="alert" className="flex items-start gap-2 text-bad-700">
          <AlertIcon className="mt-0.5 size-5 shrink-0" />
          {error}
        </p>
      )}

      {review && (
        <section aria-labelledby="review-h" className="space-y-3 rounded-2xl border border-line bg-surface p-4">
          <h2 id="review-h" className="text-[17px] font-bold">
            {t("review")}
          </h2>
          <p className="text-[14px] text-ink-2">{t("reviewHelp")}</p>
          <dl className="space-y-2">
            {review.rows.map((r) => (
              <div key={r.key}>
                <dt className="text-[13.5px] font-semibold text-ink-2">{r.label}</dt>
                <dd className="whitespace-pre-wrap text-[15px]">{r.value}</dd>
              </div>
            ))}
          </dl>
          <p className="rounded-xl bg-marigold-050 px-3 py-2 text-[13.5px] text-ink-2">{t("notice")}</p>
          <label className="flex min-h-11 items-center gap-3 text-[15px] font-semibold">
            <input type="checkbox" className="size-5" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
            {t("checked")}
          </label>
          <Button disabled={!checked || busy} onClick={onDownload}>
            {t("download")}
          </Button>
        </section>
      )}
    </div>
  );
}

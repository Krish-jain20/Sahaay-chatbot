"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AlertIcon, LinkIcon, ShieldCheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { downloadForm, loadForms, previewForm, type FormInfo, type FormPreview } from "@/lib/api";

const ADDRESS = new Set(["house", "locality", "subdivision", "state", "pin", "sub_locality", "village_town", "district", "country"]);
const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px]";

export function FormFiller() {
  const t = useTranslations("forms");
  const tt = t as unknown as (key: string, values?: Record<string, string | number>) => string;
  const [form, setForm] = useState<FormInfo | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [values, setValues] = useState<Record<string, string>>({});
  const [review, setReview] = useState<FormPreview | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    loadForms().then((list) => {
      setForm(list[0] ?? null);
      setState(list.length ? "ready" : "error");
    });
  }, []);

  function message(code: string): string {
    const [kind, a, b] = code.split(":");
    const name = (k?: string) => (k ? tt(`fields.${k}`) : "");
    if (code === "invalid_aadhaar") return t("err_invalid_aadhaar");
    if (kind === "ascii_only") return tt("err_ascii_only", { field: name(a) });
    if (kind === "too_long") return tt("err_too_long", { field: name(a), max: b });
    if (kind === "missing_required") return tt("err_missing_required", { field: name(a) });
    if (code === "changed_since_review") return t("err_changed");
    return t("err_failed");
  }

  const set = (k: string, v: string) => {
    setValues((s) => ({ ...s, [k]: v }));
    setReview(null); // any edit voids the review and the tick
    setChecked(false);
  };

  async function onReview(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    setError(null);
    const res = await previewForm(form.id, values);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    setReview(res);
  }

  async function onDownload() {
    if (!form || !review) return;
    setBusy(true);
    setError(null);
    const res = await downloadForm(form.id, values, review.hash);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    const url = URL.createObjectURL(res);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${form.id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (state === "loading") return <p className="text-ink-2">…</p>;
  if (!form || state === "error") return <p role="alert" className="text-bad-700">{t("err_failed")}</p>;

  const group = (title: string, keys: (k: string) => boolean) => (
    <fieldset className="space-y-4">
      <legend className="mb-1 text-[17px] font-bold">{title}</legend>
      {form.fields.filter((f) => keys(f.key)).map((f) => (
        <div key={f.key}>
          <label htmlFor={`f-${f.key}`} className="mb-1 block text-[14px] font-semibold text-ink-2">
            {tt(`fields.${f.key}`)}
          </label>
          <input
            id={`f-${f.key}`}
            className={input}
            maxLength={f.key === "uid" ? 14 : f.max_chars}
            inputMode={f.key === "uid" || f.key === "mobile" || f.key === "pin" ? "numeric" : undefined}
            autoComplete="off"
            value={values[f.key] ?? ""}
            onChange={(e) => set(f.key, e.target.value)}
          />
        </div>
      ))}
    </fieldset>
  );

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-line bg-surface p-4">
        <h2 className="text-[17px] font-bold">{form.title}</h2>
        <p className="mt-1 text-[13.5px] text-ink-3">
          {t("source")}: {new URL(form.source_url).host} · {t("checked")}: {form.date_checked}
        </p>
        <a
          href={form.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex min-h-11 items-center gap-2 text-[15px] font-semibold text-teal-700 underline"
        >
          <LinkIcon className="size-4" />
          {t("open")}
        </a>
      </section>

      <form onSubmit={onReview} className="space-y-6">
        {group(t("group_you"), (k) => !ADDRESS.has(k))}
        {group(t("group_address"), (k) => ADDRESS.has(k))}
        <p className="text-[13px] text-ink-3">{t("latin")}</p>
        <p className="flex items-start gap-2 text-[13px] text-ink-3">
          <ShieldCheckIcon className="mt-0.5 size-4 shrink-0" />
          {t("aadhaar")}
        </p>
        <Button type="submit" disabled={busy}>{t("preview")}</Button>
      </form>

      {error && (
        <p role="alert" className="flex items-start gap-2 text-bad-700">
          <AlertIcon className="mt-0.5 size-5 shrink-0" />
          {error}
        </p>
      )}

      {review && (
        <section aria-labelledby="form-review-h" className="space-y-3 rounded-2xl border border-line bg-surface p-4">
          <h2 id="form-review-h" className="text-[17px] font-bold">{t("review")}</h2>
          <p className="text-[14px] text-ink-2">{t("reviewHelp")}</p>
          <dl className="space-y-2">
            {Object.entries(review.values).map(([k, v]) => (
              <div key={k}>
                <dt className="text-[13.5px] font-semibold text-ink-2">{tt(`fields.${k}`)}</dt>
                <dd className="text-[15px]">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="rounded-xl bg-marigold-050 px-3 py-2 text-[13.5px] text-ink-2">{t("notice")}</p>
          <label className="flex min-h-11 items-center gap-3 text-[15px] font-semibold">
            <input type="checkbox" className="size-5" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
            {t("tick")}
          </label>
          <Button disabled={!checked || busy} onClick={onDownload}>{t("download")}</Button>
        </section>
      )}
    </div>
  );
}

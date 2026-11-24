"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { DraftIcon } from "@/components/drafts/draft-icons";
import { AlertIcon, ArrowLeftIcon, CheckIcon, LinkIcon, ShieldCheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  downloadDraft,
  previewDraft,
  type DraftCard,
  type DraftFieldDef,
  type DraftFields,
  type DraftPreview,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px]";

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Fill in, review and download one draft. The server owns the field list, validation and the PDF. */
export function DraftBuilder({ card, onBack }: { card: DraftCard; onBack: () => void }) {
  const t = useTranslations("drafts");
  const locale = useLocale();
  const [lang, setLang] = useState<"en" | "hi">(locale === "hi" ? "hi" : "en");
  const [values, setValues] = useState<DraftFields>({});
  const [review, setReview] = useState<DraftPreview | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const reviewRef = useRef<HTMLHeadingElement>(null);

  const label = (key: string) => card.fields.find((f) => f.key === key)?.label ?? key;
  const set = (k: string, v: string | boolean) => {
    setValues((s) => ({ ...s, [k]: v }));
    // Any edit after review invalidates the review and the tick.
    setReview(null);
    setChecked(false);
  };

  useEffect(() => {
    if (review) reviewRef.current?.focus();
  }, [review]);

  function message(code: string): string {
    const [name, list] = code.split(":");
    if (list && ["missing_required", "invalid_date", "future_date", "invalid_choice"].includes(name)) {
      const key = name === "missing_required" ? "missing" : name;
      return t(key, { fields: list.split(",").map(label).join(", ") });
    }
    return code === "changed_since_review" ? t("changed") : t("failed");
  }

  async function onReview(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await previewDraft(card.id, lang, values);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    setReview(res);
    setChecked(false);
  }

  async function onDownload() {
    if (!review) return;
    setBusy(true);
    setError(null);
    const res = await downloadDraft(card.id, lang, values, review.hash);
    setBusy(false);
    if ("error" in res) return setError(message(res.error));
    const url = URL.createObjectURL(res);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sahaay-${card.id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const step = checked ? 3 : review ? 2 : 1;
  const steps = [t("stepFill"), t("stepReview"), t("stepDownload")];

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        className="-ml-2 inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-[14.5px] font-semibold text-teal-700 hover:bg-teal-100"
      >
        <ArrowLeftIcon className="size-5" />
        {t("back")}
      </button>

      <header className="flex items-start gap-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-teal-700 text-white">
          <DraftIcon name={card.icon} className="size-7" />
        </span>
        <div>
          <h2 className="text-[26px] font-extrabold leading-[1.1] sm:text-[30px]">{card.title}</h2>
          <p className="mt-1.5 text-ink-2">{card.blurb}</p>
        </div>
      </header>

      <ol aria-label={t("stepsLabel")} className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {steps.map((name, i) => {
          const n = i + 1;
          const done = n < step;
          const current = n === step;
          return (
            <li key={name} aria-current={current ? "step" : undefined} className="flex items-center gap-2 text-[14px] font-semibold">
              <span
                className={cn(
                  "grid size-7 place-items-center rounded-full border text-[13px]",
                  done && "border-teal-700 bg-teal-700 text-white",
                  current && "border-marigold-500 bg-marigold-500 text-ink",
                  !done && !current && "border-line bg-surface text-ink-3",
                )}
              >
                {done ? <CheckIcon className="size-4" /> : n}
              </span>
              <span className={current || done ? "text-ink" : "text-ink-3"}>{name}</span>
              {n < 3 && <span aria-hidden className="ml-1 h-px w-6 bg-line" />}
            </li>
          );
        })}
      </ol>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
        <div className="space-y-5">
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

          <form onSubmit={onReview} className="space-y-4" noValidate>
            {card.fields.map((f) => (
              <FieldInput key={f.key} f={f} value={values[f.key]} onChange={(v) => set(f.key, v)} />
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
              <h2 id="review-h" ref={reviewRef} tabIndex={-1} className="text-[17px] font-bold outline-none">
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
              <p className="text-[13px] text-ink-3">{t("lastStep")}</p>
            </section>
          )}
        </div>

        <aside aria-labelledby="before-h" className="space-y-4 rounded-2xl border border-line bg-bg-panel p-5 lg:sticky lg:top-6">
          <h3 id="before-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("before")}
          </h3>
          {card.enclose && (
            <div>
              <p className="text-[13.5px] font-semibold text-ink-2">{t("keepReady")}</p>
              <p className="mt-1 text-[14.5px]">{card.enclose}</p>
            </div>
          )}
          {card.portal && (
            <div>
              <p className="text-[13.5px] font-semibold text-ink-2">{t("portal")}</p>
              <a
                href={card.portal.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-flex min-h-11 items-center gap-2 break-all font-semibold text-teal-700 underline underline-offset-2"
              >
                <LinkIcon className="size-4 shrink-0" />
                {card.portal.host}
              </a>
              <p className="text-[12.5px] text-ink-3">
                {t("portalNote")}
                {card.portal.date_checked && ` · ${t("checkedOn", { date: card.portal.date_checked })}`}
              </p>
            </div>
          )}
          <p className="rounded-xl bg-marigold-050 px-3 py-2 text-[13.5px] text-ink-2">{t("notice")}</p>
        </aside>
      </div>
    </div>
  );
}

function FieldInput({
  f,
  value,
  onChange,
}: {
  f: DraftFieldDef;
  value: string | boolean | undefined;
  onChange: (v: string | boolean) => void;
}) {
  const t = useTranslations("drafts");
  const id = `d-${f.key}`;
  if (f.type === "checkbox") {
    return (
      <label className="flex min-h-11 items-center gap-3 text-[15px]">
        <input type="checkbox" className="size-5" checked={value === true} onChange={(e) => onChange(e.target.checked)} />
        {f.label}
      </label>
    );
  }
  const text = (value as string) ?? "";
  const heading = (
    <span className="mb-1 block text-[14px] font-semibold text-ink-2">
      {f.label}
      {!f.required && <span className="font-normal text-ink-3"> ({t("optional")})</span>}
    </span>
  );
  if (f.type === "choice") {
    return (
      <fieldset>
        <legend className="mb-1.5 text-[14px] font-semibold text-ink-2">{f.label}</legend>
        <div className="flex flex-wrap gap-2">
          {f.options.map((o) => (
            <label
              key={o.id}
              className={cn(
                "flex min-h-11 cursor-pointer items-center gap-2 rounded-full border px-4 text-[14.5px] font-medium transition-colors focus-within:ring-[3px] focus-within:ring-teal-700/40",
                text === o.id ? "border-teal-700 bg-teal-700 text-white" : "border-line bg-surface text-ink hover:border-teal-700",
              )}
            >
              <input
                type="radio"
                name={id}
                value={o.id}
                checked={text === o.id}
                onChange={() => onChange(o.id)}
                className="sr-only"
              />
              {text === o.id && <CheckIcon className="size-4" />}
              {o.label}
            </label>
          ))}
        </div>
      </fieldset>
    );
  }
  return (
    <div>
      <label htmlFor={id} className="block">
        {heading}
      </label>
      {f.type === "multiline" ? (
        <textarea id={id} rows={4} className={input} value={text} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input
          id={id}
          type={f.type === "date" ? "date" : "text"}
          max={f.type === "date" ? today() : undefined}
          className={input}
          value={text}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={f.hint ? `${id}-hint` : undefined}
        />
      )}
      {f.hint && (
        <p id={`${id}-hint`} className="mt-1 text-[12.5px] text-ink-3">
          {f.hint}
        </p>
      )}
    </div>
  );
}

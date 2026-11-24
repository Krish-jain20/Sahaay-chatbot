"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AlertIcon, CheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { downloadSummary, openCase, recordStep, undoStep, type CaseView, type Journey, type Submission } from "@/lib/api";
import { API_URL } from "@/lib/sse";
import { cn } from "@/lib/utils";

interface ServiceLite {
  id: string;
  name: { en: string | null; hi: string | null; hn: string | null };
}

const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px] md:w-72";

export function CaseFolder() {
  const t = useTranslations("case");
  const tt = t as unknown as (key: string, values?: Record<string, string | number>) => string;
  const locale = useLocale() as "en" | "hi" | "hn";
  const [services, setServices] = useState<ServiceLite[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [view, setView] = useState<CaseView | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/services`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((list: ServiceLite[]) => {
        setServices(list);
        setServiceId(list[0]?.id ?? "");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    if (!serviceId) return;
    setState("loading");
    setView(null);
    openCase(serviceId).then((c) => {
      if (!c) return setState("error");
      setView(c);
      setSubmission(c);
      setState("ready");
    });
  }, [serviceId]);

  function setSubmission(c: CaseView) {
    setDate(c.submission?.submitted_on ?? "");
    setReference("");
  }

  function apply(r: { journey: Journey; submission: Submission | null }) {
    setView((v) => (v ? { ...v, journey: r.journey, submission: r.submission } : v));
  }

  async function mark(step: number) {
    if (!view) return;
    setError(null);
    const extra: { submitted_on?: string; reference?: string } = {};
    if (step === 4 && date) extra.submitted_on = date;
    if (step === 5) extra.reference = reference;
    if (step === 4 && date && date > new Date().toISOString().slice(0, 10)) return setError(t("futureDate"));
    if (step === 5 && reference.replace(/[^A-Za-z0-9]/g, "").length < 4) return setError(t("tooShort"));
    setBusy(true);
    const res = await recordStep(view.id, step, extra);
    setBusy(false);
    if ("error" in res) return setError(t("saveError"));
    apply(res);
  }

  async function undo(step: number) {
    if (!view) return;
    setBusy(true);
    const res = await undoStep(view.id, step);
    setBusy(false);
    if (res) apply(res);
    else setError(t("saveError"));
  }

  async function onSummary() {
    if (!view) return;
    const blob = await downloadSummary(view.id, locale);
    if (!blob) return setError(t("saveError"));
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sahaay-case-summary.pdf";
    a.click();
    URL.revokeObjectURL(url);
  }

  const j = view?.journey;
  const nextKey = j?.current ? `n${j.current}` : "n6";

  return (
    <div className="space-y-5">
      <div>
        <label htmlFor="case-service" className="mb-1 block text-[14px] font-semibold text-ink-2">
          {t("service")}
        </label>
        <select
          id="case-service"
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
          {t("error")}
        </p>
      )}

      {state === "ready" && view && j && (
        <>
          <section aria-labelledby="tracker-h" className="rounded-2xl border border-line bg-surface p-4">
            <h2 id="tracker-h" className="text-[17px] font-bold">
              {t("own")}
            </h2>
            <ol className="mt-4 space-y-3">
              {j.steps.map((s) => {
                const isCurrent = j.current === s.n;
                return (
                  <li key={s.n} className="flex flex-wrap items-center gap-3" aria-current={isCurrent ? "step" : undefined}>
                    <span
                      aria-hidden
                      className={cn(
                        "flex size-9 shrink-0 items-center justify-center rounded-full border-2 text-[14px] font-bold",
                        s.done && "border-teal-700 bg-teal-700 text-white",
                        isCurrent && "border-marigold-500 bg-marigold-500 text-ink motion-safe:animate-pulse",
                        !s.done && !isCurrent && "border-line text-ink-3",
                      )}
                    >
                      {s.done ? <CheckIcon className="size-5" /> : s.n}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[15px] font-semibold">{tt(`s${s.n}`)}</p>
                      <p className="text-[13px] text-ink-3">
                        {s.done ? `${t("done")}${s.done_at ? ` · ${s.done_at.slice(0, 10)}` : ""}` : isCurrent ? t("current") : t("upcoming")}
                      </p>
                    </div>
                    {s.done ? (
                      <Button variant="ghost" disabled={busy} onClick={() => undo(s.n)} aria-label={`${t("undo")}: ${tt(`s${s.n}`)}`}>
                        {t("undo")}
                      </Button>
                    ) : (
                      isCurrent && s.n !== 4 && s.n !== 5 && (
                        <Button variant="secondary" disabled={busy} onClick={() => mark(s.n)} aria-label={`${t("mark")}: ${tt(`s${s.n}`)}`}>
                          {t("mark")}
                        </Button>
                      )
                    )}
                  </li>
                );
              })}
            </ol>

            {(j.current === 4 || j.current === 5) && (
              <div className="mt-4 space-y-3 rounded-xl bg-bg-sunken p-4">
                {j.current === 4 && (
                  <div>
                    <label htmlFor="sub-date" className="mb-1 block text-[14px] font-semibold text-ink-2">
                      {t("submittedOn")}
                    </label>
                    <input id="sub-date" type="date" className={input} value={date} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)} />
                  </div>
                )}
                {j.current === 5 && (
                  <div>
                    <label htmlFor="sub-ref" className="mb-1 block text-[14px] font-semibold text-ink-2">
                      {t("reference")}
                    </label>
                    <input id="sub-ref" autoComplete="off" className={input} value={reference} onChange={(e) => setReference(e.target.value)} />
                  </div>
                )}
                <Button disabled={busy} onClick={() => mark(j.current!)} aria-label={`${t("mark")}: ${tt(`s${j.current}`)}`}>
                  {t("mark")}
                </Button>
              </div>
            )}

            {view.submission?.submitted_on && (
              <p className="mt-3 text-[14px] text-ink-2">{tt("submittedDate", { date: view.submission.submitted_on })}</p>
            )}
            {view.submission?.reference_no_masked && (
              <p className="text-[14px] text-ink-2">{tt("referenceKept", { ref: view.submission.reference_no_masked })}</p>
            )}
            {error && (
              <p role="alert" className="mt-3 flex items-start gap-2 text-bad-700">
                <AlertIcon className="mt-0.5 size-5 shrink-0" />
                {error}
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-line bg-surface p-4">
            <h2 className="text-[17px] font-bold">{t("next")}</h2>
            <p className="mt-1 text-[15px] text-ink-2">{tt(nextKey)}</p>
          </section>

          <section className="rounded-2xl border border-line bg-surface p-4">
            <h2 className="text-[17px] font-bold">{t("readiness")}</h2>
            <p className="mt-1 text-[15px]" data-testid="case-ready">
              {tt("readyCount", { done: view.readiness.completed, total: view.readiness.total })}
            </p>
            <p className="text-[13.5px] text-ink-3">{t("readyCaption")}</p>
          </section>

          <div className="flex flex-wrap gap-2">
            <Button asChild variant="secondary"><Link href="/chat">{t("openChat")}</Link></Button>
            <Button asChild variant="secondary"><Link href="/documents">{t("openDocs")}</Link></Button>
            <Button asChild variant="secondary"><Link href="/forms">{t("openForm")}</Link></Button>
            <Button asChild variant="secondary"><Link href="/drafts">{t("openDrafts")}</Link></Button>
            <Button asChild variant="secondary"><Link href="/help/complaints">{t("openHelp")}</Link></Button>
            <Button onClick={onSummary}>{t("summary")}</Button>
          </div>
        </>
      )}
    </div>
  );
}

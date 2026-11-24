"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { WebCard } from "@/components/cards/web-card";
import { ChevronDownIcon } from "@/components/icons";
import { askHelp, explainHelpCard, type HelpAnswer, type HelpExplanation } from "@/lib/api";
import { API_URL } from "@/lib/sse";
import type { GuideCardData } from "@/lib/types";
import { cn } from "@/lib/utils";

type Point = GuideCardData["points"][number];

function scrollToCard(id: string) {
  requestAnimationFrame(() => document.getElementById(`card-${id}`)?.scrollIntoView({ block: "center", behavior: "smooth" }));
}

export function HelpHub() {
  const t = useTranslations("help");
  const locale = useLocale();
  const [sections, setSections] = useState<GuideCardData[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [open, setOpen] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [reply, setReply] = useState<HelpAnswer | "failed" | null>(null);
  const [highlight, setHighlight] = useState<string[]>([]);

  useEffect(() => {
    setState("loading");
    fetch(`${API_URL}/help?lang=${locale}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((b: { sections: GuideCardData[] }) => {
        setSections(b.sections);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [locale]);

  // Old links like /help#scams land on the matching section.
  useEffect(() => {
    if (state !== "ready" || !window.location.hash) return;
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "start" });
  }, [state]);

  const q = filter.trim().toLowerCase();
  const visible = useMemo(
    () =>
      sections
        .map((s) => ({
          ...s,
          points: q ? s.points.filter((p) => `${p.heading} ${p.body}`.toLowerCase().includes(q)) : s.points,
        }))
        .filter((s) => s.points.length > 0),
    [sections, q],
  );
  const total = visible.reduce((n, s) => n + s.points.length, 0);

  const names = useMemo(() => {
    const m = new Map<string, string>();
    for (const s of sections) for (const p of s.points) m.set(`${s.id}.${p.id}`, p.heading);
    return m;
  }, [sections]);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const text = question.trim();
    if (text.length < 2) return;
    setAsking(true);
    setFilter("");
    const r = await askHelp(text, locale);
    setAsking(false);
    setReply(r ?? "failed");
    setHighlight(r?.matches ?? []);
    if (r?.matches[0]) {
      setOpen(r.matches[0]);
      scrollToCard(r.matches[0]);
    }
  }

  function jump(id: string) {
    setOpen(id);
    scrollToCard(id);
  }

  return (
    <div className="space-y-6">
      <p className="text-ink-2">{t("intro")}</p>

      <form onSubmit={ask} className="space-y-2 rounded-2xl border border-line bg-surface p-4" data-testid="help-ask">
        <label htmlFor="help-q" className="block text-[16px] font-semibold">{t("askLabel")}</label>
        <p className="text-[13.5px] text-ink-3">{t("askHelp")}</p>
        <div className="flex flex-wrap gap-2">
          <input
            id="help-q"
            value={question}
            maxLength={300}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={t("askPlaceholder")}
            className="min-h-11 min-w-0 flex-1 rounded-xl border border-line bg-bg px-3 text-[16px]"
          />
          <button type="submit" disabled={asking} className="min-h-11 rounded-full bg-teal-700 px-5 text-[15px] font-semibold text-white disabled:opacity-60">
            {asking ? t("asking") : t("ask")}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {(["ex1", "ex2", "ex3"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setQuestion(t(k))}
              className="min-h-11 rounded-full border border-line bg-bg px-3 text-[14px] text-ink-2"
            >
              {t(k)}
            </button>
          ))}
        </div>
      </form>

      {reply && (
        <section aria-labelledby="ans-title" className="space-y-3 rounded-2xl border border-teal-700 bg-surface p-4" data-testid="help-answer">
          <h2 id="ans-title" className="font-display text-[19px] font-bold">{t("answerTitle")}</h2>
          {reply === "failed" ? (
            <p role="status">{t("askFailed")}</p>
          ) : (
            <>
              {reply.answer ? (
                <>
                  <p className="text-[13.5px] font-semibold text-ink-3">
                    {reply.basis === "web" ? t("aiNote") : reply.basis === "cards" ? t("askCardsNote") : t("askCardTextNote")}
                  </p>
                  <p data-testid="help-answer-text">{reply.answer}</p>
                  {reply.web && <WebCard card={reply.web} />}
                </>
              ) : (
                <p role="status" data-testid="help-answer-none">{t("noAnswer")}</p>
              )}
              {reply.matches.length > 0 && (
                <div>
                  <h3 className="text-[14px] font-semibold text-ink-2">{t("related")}</h3>
                  <ul className="mt-1 flex flex-wrap gap-2">
                    {reply.matches.map((id) => (
                      <li key={id}>
                        <button type="button" onClick={() => jump(id)} className="min-h-11 rounded-full border border-teal-700 px-3 text-[14px] text-teal-700">
                          {names.get(id) ?? id}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </section>
      )}

      <div>
        <label htmlFor="help-filter" className="mb-1 block text-[15px] font-semibold">{t("filter")}</label>
        <input
          id="help-filter"
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="min-h-11 w-full rounded-xl border border-line bg-bg px-3 text-[16px]"
        />
        <p className="mt-1 text-[13.5px] text-ink-3" role="status">{t("count", { n: total })}</p>
      </div>

      {state === "error" && <p role="alert" className="text-bad-700">{t("error")}</p>}
      {state === "loading" && <p role="status" className="text-ink-3">{t("loading")}</p>}

      {visible.length > 1 && (
        <nav aria-label={t("jump")} className="flex flex-wrap gap-2">
          {visible.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="inline-flex min-h-11 items-center rounded-full border border-line bg-surface px-4 text-[14.5px] text-ink-2">
              {s.title}
            </a>
          ))}
        </nav>
      )}

      {visible.map((s) => (
        <section key={s.id} id={s.id} aria-labelledby={`${s.id}-h`} className="scroll-mt-4 space-y-3" data-testid={`help-section-${s.id}`}>
          <header>
            <h2 id={`${s.id}-h`} className="font-display text-[22px] font-bold">{s.title}</h2>
            <p className="text-[15px] text-ink-2">{s.intro}</p>
          </header>
          <ul className="space-y-3">
            {s.points.map((p) => {
              const id = `${s.id}.${p.id}`;
              return (
                <li key={id}>
                  <HelpCard id={id} point={p} open={open === id} lit={highlight.includes(id)} onToggle={() => setOpen(open === id ? null : id)} />
                </li>
              );
            })}
          </ul>
          <div className="text-[14px]">
            <h3 className="font-semibold text-ink-2">{t("sources")}</h3>
            <ul className="mt-1 space-y-1">
              {s.citations.map((c) => (
                <li key={c.n}>
                  [{c.n}] {c.publisher}:{" "}
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="break-all text-teal-700 underline">
                    {c.url}
                  </a>{" "}
                  <span className="text-ink-3">{c.date_checked ? t("checkedOn", { date: c.date_checked }) : t("notChecked")}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ))}
      <p className="text-[13.5px] text-ink-3">{t("note")}</p>
    </div>
  );
}

function HelpCard({ id, point, open, lit, onToggle }: { id: string; point: Point; open: boolean; lit: boolean; onToggle: () => void }) {
  const t = useTranslations("help");
  const locale = useLocale();
  const uid = useId();
  const panelId = `${uid}-panel`;
  const [situation, setSituation] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<HelpExplanation | null>(null);
  const [failed, setFailed] = useState(false);
  const seen = useRef(locale);

  // A new language makes an explanation written in the old one wrong.
  useEffect(() => {
    if (seen.current !== locale) {
      seen.current = locale;
      setResult(null);
    }
  }, [locale]);

  async function explain(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFailed(false);
    const r = await explainHelpCard(id, locale, situation.trim());
    setBusy(false);
    if (r) setResult(r);
    else setFailed(true);
  }

  return (
    <article
      id={`card-${id}`}
      data-testid={`help-card-${id}`}
      className={cn("scroll-mt-4 rounded-2xl border bg-surface", open ? "border-teal-700" : lit ? "border-marigold-500 ring-2 ring-marigold-500" : "border-line")}
    >
      <h3 className="m-0">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
          className="flex min-h-11 w-full items-start gap-3 rounded-2xl p-4 text-left"
        >
          <span className="min-w-0 flex-1 font-display text-[17px] font-bold text-ink">
            {point.heading}
            {lit && <span className="ml-2 rounded-full bg-marigold-500 px-2 py-0.5 align-middle font-sans text-[12px] font-semibold text-ink">{t("matches")}</span>}
          </span>
          <ChevronDownIcon className={cn("mt-1 size-5 shrink-0 text-teal-700 transition-transform motion-reduce:transition-none", open && "rotate-180")} />
        </button>
      </h3>
      <div id={panelId} role="region" aria-label={point.heading} hidden={!open} className="space-y-4 border-t border-line p-4">
        <p className="text-[15.5px] text-ink-2">
          {point.body}{" "}
          {point.source_n !== null && (
            <sup className="font-bold text-teal-700" aria-label={t("source", { n: point.source_n })}>[{point.source_n}]</sup>
          )}
        </p>
        <form onSubmit={explain} className="space-y-2 rounded-xl bg-bg-sunken p-3">
          <label htmlFor={`${uid}-sit`} className="block text-[14px] font-semibold">{t("situationLabel")}</label>
          <div className="flex flex-wrap gap-2">
            <input
              id={`${uid}-sit`}
              value={situation}
              maxLength={200}
              onChange={(e) => setSituation(e.target.value)}
              placeholder={t("situationPlaceholder")}
              className="min-h-11 w-full min-w-0 rounded-xl border border-line bg-surface px-3 text-[16px] sm:w-auto sm:flex-1"
            />
            <button type="submit" disabled={busy} className="min-h-11 rounded-full border border-teal-700 px-4 text-[14.5px] font-semibold text-teal-700 disabled:opacity-60">
              {busy ? t("explaining") : t("explain")}
            </button>
          </div>
          {result && (
            <div role="status" data-testid="help-explanation" className="space-y-2">
              <p className="text-[12.5px] font-semibold text-ink-3">{result.web ? t("explainNote") : t("explainNoteCard")}</p>
              <p className="whitespace-pre-line">{result.text}</p>
              {result.web && <WebCard card={result.web} />}
            </div>
          )}
          {failed && <p role="status" className="text-[14px] text-ink-2">{t("explainFailed")}</p>}
        </form>
      </div>
    </article>
  );
}

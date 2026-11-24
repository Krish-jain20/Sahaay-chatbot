"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useMemo, useState } from "react";

import { AlertIcon, ChevronDownIcon, ShieldCheckIcon } from "@/components/icons";
import { compareWeb, type WebColumn } from "@/lib/api";
import { API_URL } from "@/lib/sse";
import { cn } from "@/lib/utils";

interface Line {
  text: string;
  source_n: number;
}
interface ServiceCard {
  id: string;
  kind: "record" | "directory";
  name: string;
  department: string;
  summary: string;
  benefit: Line | null;
  who: Line[];
  not_if: Line[];
  documents: Line[];
  fee: Line | null;
  time: Line | null;
  steps: Line[];
  apply_url: string | null;
  citations: { n: number; title: string; url: string; publisher: string; date_checked: string | null }[];
  checked_on: string | null;
  stale: boolean;
  notes: string | null;
}

const MAX_PICKED = 3;

export function CompareTable() {
  const t = useTranslations("compare");
  const tw = useTranslations("web");
  const locale = useLocale() as "en" | "hi" | "hn";
  const [cards, setCards] = useState<ServiceCard[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [open, setOpen] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [webQuery, setWebQuery] = useState("");
  const [webCol, setWebCol] = useState<WebColumn | null>(null);
  const [webState, setWebState] = useState<"idle" | "busy" | "none" | "unavailable">("idle");

  useEffect(() => {
    setState("loading");
    fetch(`${API_URL}/cards?lang=${locale}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((list: ServiceCard[]) => {
        setCards(list);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [locale]);

  // A link such as /compare#income-certificate opens that card and scrolls to it.
  useEffect(() => {
    if (state !== "ready") return;
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (!id || !cards.some((c) => c.id === id)) return;
    setOpen(id);
    requestAnimationFrame(() => document.getElementById(`card-${id}`)?.scrollIntoView({ block: "start" }));
  }, [state, cards]);

  const shown = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return q ? cards.filter((c) => `${c.name} ${c.department} ${c.summary}`.toLowerCase().includes(q)) : cards;
  }, [cards, filter]);
  const chosen = picked.map((id) => cards.find((c) => c.id === id)).filter((c): c is ServiceCard => !!c);

  function toggle(id: string) {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < MAX_PICKED ? [...p, id] : p));
  }

  async function addWeb(e: React.FormEvent) {
    e.preventDefault();
    if (!webQuery.trim()) return;
    setWebState("busy");
    const r = await compareWeb(webQuery.trim(), locale);
    if (typeof r === "string") {
      setWebState(r);
    } else {
      setWebCol(r);
      setWebState("idle");
      setWebQuery("");
    }
  }

  return (
    <div className="space-y-5">
      <p className="text-ink-2">{t("intro")}</p>

      <div>
        <label htmlFor="svc-filter" className="mb-1 block text-[15px] font-semibold">
          {t("filter")}
        </label>
        <input
          id="svc-filter"
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="min-h-11 w-full rounded-xl border border-line bg-bg px-3 text-[16px]"
        />
        <p className="mt-1 text-[13.5px] text-ink-3" role="status">
          {t("count", { n: shown.length })}
        </p>
      </div>

      {state === "error" && <p role="alert" className="text-bad-700">{t("error")}</p>}
      {state === "loading" && <p role="status" className="text-ink-3">{t("loading")}</p>}

      {chosen.length >= 2 && (
        <section aria-labelledby="side-title" className="space-y-2" data-testid="side-by-side">
          <h2 id="side-title" className="font-display text-[20px] font-bold">{t("sideBySide")}</h2>
          <SideBySide cards={chosen} onRemove={toggle} />
        </section>
      )}
      {chosen.length === 1 && <p className="text-[14px] text-ink-3">{t("pickMore")}</p>}

      <ul className="space-y-3">
        {webCol && (
          <li>
            <article className="space-y-2 rounded-2xl border border-line bg-surface p-4" data-testid="web-card-extra">
              <p className="inline-flex items-center gap-2 rounded-full bg-warn-100 px-2.5 py-0.5 text-[12.5px] font-semibold text-warn-700" data-testid="web-col-head">
                <AlertIcon className="size-4" />
                {t("webBadge")}
              </p>
              <h2 className="font-display text-[18px] font-bold">{webCol.name}</h2>
              <p data-testid="web-summary">{webCol.summary}</p>
              <ul className="space-y-1 text-[14px]">
                {webCol.web.sources.map((c) => (
                  <li key={c.n}>
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                      [{c.n}] {c.title}
                    </a>{" "}
                    <span className="text-ink-3">
                      {c.kind === "gov_unchecked" ? tw("govUnchecked") : c.official ? tw("official") : tw("unofficial")}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-[13.5px] text-ink-3">{tw("retrieved", { date: webCol.web.retrieved_on })}</p>
              <button type="button" onClick={() => setWebCol(null)} className="min-h-11 text-[14px] text-teal-700 underline">
                {t("webRemove")}
              </button>
            </article>
          </li>
        )}
        {shown.map((c) => (
          <li key={c.id} id={`card-${c.id}`} className="scroll-mt-24">
            <ServiceCardView
              card={c}
              open={open === c.id}
              onToggleOpen={() => setOpen(open === c.id ? null : c.id)}
              picked={picked.includes(c.id)}
              pickDisabled={!picked.includes(c.id) && picked.length >= MAX_PICKED}
              onPick={() => toggle(c.id)}
            />
          </li>
        ))}
      </ul>
      {state === "ready" && shown.length === 0 && <p className="text-ink-2">{t("empty")}</p>}

      <form onSubmit={addWeb} className="space-y-2 rounded-2xl border border-line bg-surface p-4" data-testid="web-add">
        <label htmlFor="web-q" className="block text-[15px] font-semibold">{t("webAdd")}</label>
        <p className="text-[13.5px] text-ink-3">{t("webAddHelp")}</p>
        <div className="flex flex-wrap gap-2">
          <input
            id="web-q"
            value={webQuery}
            maxLength={80}
            onChange={(e) => setWebQuery(e.target.value)}
            className="min-h-11 min-w-0 flex-1 rounded-xl border border-line bg-bg px-3 text-[16px]"
          />
          <button type="submit" disabled={webState === "busy"} className="min-h-11 rounded-full bg-teal-700 px-5 text-[15px] font-semibold text-white disabled:opacity-60">
            {webState === "busy" ? t("webBusy") : t("webSearch")}
          </button>
        </div>
        {webState === "none" && <p role="status" className="text-ink-2">{t("webNone")}</p>}
        {webState === "unavailable" && <p role="status" className="text-ink-2">{t("webUnavailable")}</p>}
      </form>
    </div>
  );
}

function ServiceCardView({
  card,
  open,
  onToggleOpen,
  picked,
  pickDisabled,
  onPick,
}: {
  card: ServiceCard;
  open: boolean;
  onToggleOpen: () => void;
  picked: boolean;
  pickDisabled: boolean;
  onPick: () => void;
}) {
  const t = useTranslations("compare");
  const tc = useTranslations("card");
  const locale = useLocale();
  const uid = useId();
  const panelId = `${uid}-panel`;
  return (
    <article className={cn("rounded-2xl border bg-surface", open ? "border-teal-700" : "border-line")} data-testid="service-card">
      <h2 className="m-0">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggleOpen}
          className="flex min-h-11 w-full items-start gap-3 rounded-2xl p-4 text-left"
        >
          <span className="min-w-0 flex-1">
            <span className="block font-display text-[18px] font-bold text-ink">{card.name}</span>
            <span className="block text-[13.5px] text-ink-3">{card.department}</span>
            <span className="mt-1 block text-[15px] text-ink-2">{card.summary}</span>
          </span>
          <ChevronDownIcon className={cn("mt-1 size-5 shrink-0 text-teal-700 transition-transform motion-reduce:transition-none", open && "rotate-180")} />
        </button>
      </h2>
      <div id={panelId} role="region" aria-label={card.name} hidden={!open} className="space-y-4 border-t border-line p-4">
        <p
          className={cn(
            "flex w-fit items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12.5px] font-semibold",
            card.stale ? "bg-warn-100 text-warn-700" : "bg-ok-100 text-ok-700",
          )}
        >
          {card.stale ? <AlertIcon className="size-4" /> : <ShieldCheckIcon className="size-4" />}
          {card.checked_on ? tc("checkedOn", { date: card.checked_on }) : tc("notChecked")}
        </p>
        {card.kind === "directory" && locale !== "en" && <p className="text-[13.5px] text-ink-3">{t("englishOnly")}</p>}
        <Detail title={t("benefit")} lines={card.benefit ? [card.benefit] : []} />
        <Detail title={t("who")} lines={card.who} list />
        {card.not_if.length > 0 && <Detail title={t("exclusions")} lines={card.not_if} list />}
        <Detail title={t("documents")} lines={card.documents} list />
        <Detail title={tc("officialFee")} lines={card.fee ? [card.fee] : []} />
        <Detail title={tc("processing")} lines={card.time ? [card.time] : []} />
        <Detail title={t("steps")} lines={card.steps} list ordered />
        {card.notes && <p className="text-[13.5px] text-ink-3">{card.notes}</p>}
        <div>
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.05em] text-ink-3">{t("sources")}</h3>
          <ul className="mt-1 space-y-1 text-[14px]">
            {card.citations.map((c) => (
              <li key={c.n}>
                <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                  [{c.n}] {c.title}
                </a>
                <span className="block text-[12.5px] text-ink-3">
                  {c.date_checked ? tc("checkedOn", { date: c.date_checked }) : tc("notChecked")}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          {card.apply_url && (
            <a href={card.apply_url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center rounded-full bg-teal-700 px-5 text-[15px] font-semibold text-white">
              {tc("openPortal")}
            </a>
          )}
          <label className="inline-flex min-h-11 items-center gap-2 text-[15px]">
            <input type="checkbox" checked={picked} disabled={pickDisabled} onChange={onPick} className="size-5" />
            {t("addToCompare", { name: card.name })}
          </label>
        </div>
      </div>
    </article>
  );
}

function Detail({ title, lines, list, ordered }: { title: string; lines: Line[]; list?: boolean; ordered?: boolean }) {
  const tc = useTranslations("card");
  return (
    <div>
      <h3 className="text-[13px] font-semibold uppercase tracking-[0.05em] text-ink-3">{title}</h3>
      {lines.length === 0 ? (
        <p className="mt-1 text-ink-3">{tc("verifyLocally")}</p>
      ) : list ? (
        <ListTag ordered={ordered}>
          {lines.map((l, i) => (
            <li key={i}>
              {l.text} <Ref n={l.source_n} />
            </li>
          ))}
        </ListTag>
      ) : (
        <p className="mt-1">
          {lines[0].text} <Ref n={lines[0].source_n} />
        </p>
      )}
    </div>
  );
}

function ListTag({ ordered, children }: { ordered?: boolean; children: React.ReactNode }) {
  const cls = cn("mt-1 space-y-1 pl-5", ordered ? "list-decimal" : "list-disc");
  return ordered ? <ol className={cls}>{children}</ol> : <ul className={cls}>{children}</ul>;
}

function Ref({ n }: { n: number }) {
  return <span className="text-[12.5px] text-ink-3">[{n}]</span>;
}

function SideBySide({ cards, onRemove }: { cards: ServiceCard[]; onRemove: (id: string) => void }) {
  const t = useTranslations("compare");
  const tc = useTranslations("card");
  const rows: { label: string; cell: (c: ServiceCard) => React.ReactNode }[] = [
    { label: t("department"), cell: (c) => c.department },
    { label: t("benefit"), cell: (c) => <One line={c.benefit} /> },
    { label: t("who"), cell: (c) => <Many lines={c.who} /> },
    { label: t("documents"), cell: (c) => <Many lines={c.documents} /> },
    { label: tc("officialFee"), cell: (c) => <One line={c.fee} /> },
    { label: tc("processing"), cell: (c) => <One line={c.time} /> },
    {
      label: t("sources"),
      cell: (c) => (
        <ul className="space-y-1">
          {c.citations.map((s) => (
            <li key={s.n}>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                [{s.n}] {s.title}
              </a>
            </li>
          ))}
        </ul>
      ),
    },
  ];
  return (
    <div className="overflow-x-auto rounded-[20px] border border-line bg-surface">
      <table className="w-full min-w-[34rem] border-collapse text-left text-[15px]">
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className="sr-only">{t("title")}</th>
            {cards.map((c) => (
              <th key={c.id} scope="col" className="p-3 align-top font-display text-[17px] font-bold">
                {c.name}
                <button type="button" onClick={() => onRemove(c.id)} className="mt-1 block min-h-11 font-sans text-[13.5px] font-normal text-teal-700 underline">
                  {t("removeFromCompare")}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-line last:border-0">
              <th scope="row" className="w-32 p-3 align-top text-[13px] font-semibold uppercase tracking-[0.05em] text-ink-3">
                {r.label}
              </th>
              {cards.map((c) => (
                <td key={c.id} className="p-3 align-top">
                  {r.cell(c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function One({ line }: { line: Line | null }) {
  const tc = useTranslations("card");
  return line ? <>{line.text}</> : <span className="text-ink-3">{tc("verifyLocally")}</span>;
}

function Many({ lines }: { lines: Line[] }) {
  const tc = useTranslations("card");
  if (!lines.length) return <span className="text-ink-3">{tc("verifyLocally")}</span>;
  return (
    <ul className="list-disc space-y-1 pl-4">
      {lines.map((l, i) => (
        <li key={i}>{l.text}</li>
      ))}
    </ul>
  );
}

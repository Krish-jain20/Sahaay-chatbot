"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AddService } from "@/components/case/add-service";
import { CaseDetail } from "@/components/case/case-detail";
import { CaseTile } from "@/components/case/case-tile";
import { ArrowLeftIcon, ArrowRightIcon, FolderIcon, PenIcon, SearchIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { loadCases, startCase, type CaseCard } from "@/lib/api";
import { API_URL } from "@/lib/sse";

interface ServiceLite {
  id: string;
  name: { en: string | null; hi: string | null; hn: string | null };
  department: { en: string | null; hi: string | null; hn: string | null };
}

function param(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name);
}

type Filter = "all" | "action" | "waiting" | "done";
type Sort = "recent" | "date" | "progress";
const FILTERS: Filter[] = ["all", "action", "waiting", "done"];
const SORTS: Sort[] = ["recent", "date", "progress"];
const selectCls = "min-h-11 rounded-xl border border-line bg-surface px-3 text-[15px]";

function bucket(c: CaseCard): Exclude<Filter, "all"> {
  if (c.overview.next_action === "done") return "done";
  if (c.overview.next_action === "wait") return "waiting";
  return "action";
}

/** Search, filter and sort the user's own cases. Pure, so it is easy to reason about. */
export function arrange(cases: CaseCard[], q: string, filter: Filter, sort: Sort): CaseCard[] {
  const needle = q.trim().toLowerCase();
  const out = cases.filter(
    (c) =>
      (filter === "all" || bucket(c) === filter) &&
      (!needle || `${c.service_name ?? ""} ${c.department ?? ""}`.toLowerCase().includes(needle)),
  );
  if (sort === "date") {
    // Cases with an upcoming date first (nearest first), then passed dates, then cases with none.
    const rank = (c: CaseCard) => (c.key_date ? (c.key_date.passed ? 1e6 - c.key_date.days_left : c.key_date.days_left) : 2e6);
    out.sort((a, b) => rank(a) - rank(b));
  } else if (sort === "progress") {
    out.sort((a, b) => a.overview.steps_done - b.overview.steps_done);
  }
  return out;
}

/** My cases: the services you are tracking, what each one needs next, and where to go to do it. */
export function MyCases() {
  const t = useTranslations("case");
  const locale = useLocale() as "en" | "hi" | "hn";
  const [cases, setCases] = useState<CaseCard[] | null>(null);
  const [services, setServices] = useState<ServiceLite[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [starting, setStarting] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<Sort>("recent");

  const refresh = useCallback(async () => {
    const list = await loadCases(locale);
    if (list === null) return setState("error");
    setCases(list);
    setState("ready");
  }, [locale]);

  const select = useCallback((id: string | null) => {
    setSelected(id);
    window.history.pushState(null, "", id ? `?case=${id}` : window.location.pathname);
    window.scrollTo({ top: 0 });
  }, []);

  const start = useCallback(
    async (serviceId: string) => {
      setStarting(serviceId);
      const id = await startCase(serviceId);
      setStarting(null);
      if (!id) return setState("error");
      await refresh();
      select(id);
    },
    [refresh, select],
  );

  useEffect(() => {
    fetch(`${API_URL}/services`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((list: ServiceLite[]) => setServices(list))
      .catch(() => setState("error"));
    void (async () => {
      // "Track this" links arrive as /case?start=<service id>: one tap starts the case and opens it.
      const wanted = param("start");
      if (wanted) {
        const id = await startCase(wanted);
        if (id) {
          setSelected(id);
          window.history.replaceState(null, "", `?case=${id}`);
        }
      } else {
        setSelected(param("case"));
      }
      await refresh();
    })();
    const onPop = () => setSelected(param("case"));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [refresh]);

  const shown = useMemo(() => arrange(cases ?? [], q, filter, sort), [cases, q, filter, sort]);

  if (state === "loading") return <p className="text-ink-2">{t("loading")}</p>;
  if (state === "error" || cases === null)
    return (
      <p role="alert" className="text-bad-700">
        {t("error")}
      </p>
    );

  const open = selected ? cases.find((c) => c.id === selected) : undefined;
  if (open) {
    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => select(null)}
          className="inline-flex min-h-11 items-center gap-2 text-[15px] font-semibold text-teal-700 underline decoration-teal-700/30 underline-offset-4"
        >
          <ArrowLeftIcon className="size-4" />
          {t("back")}
        </button>
        <CaseDetail card={open} onChange={refresh} onClose={() => select(null)} />
      </div>
    );
  }

  if (adding) {
    return (
      <AddService
        onCancel={() => setAdding(false)}
        onSaved={async (card) => {
          setAdding(false);
          await refresh();
          select(card.id);
        }}
      />
    );
  }

  const tracked = new Set(cases.map((c) => c.service_id));
  const notStarted = services.filter((s) => !tracked.has(s.id));
  const tf = t as unknown as (key: string, values?: Record<string, string | number>) => string;

  const addCard = (
    <section aria-labelledby="add-own-h" className="flex flex-col gap-3 rounded-[20px] border border-dashed border-teal-700/50 bg-teal-100/40 p-5 sm:flex-row sm:items-center">
      <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-teal-100 text-teal-700">
        <PenIcon className="size-6" />
      </span>
      <div className="min-w-0 flex-1">
        <h2 id="add-own-h" className="font-display text-[19px] font-bold leading-tight">{t("addTitle")}</h2>
        <p className="mt-0.5 text-[14.5px] text-ink-2">{t("addHelp")}</p>
      </div>
      <Button className="self-start sm:self-center" onClick={() => { setAdding(true); window.scrollTo({ top: 0 }); }} data-testid="add-own">
        {t("addButton")}
      </Button>
    </section>
  );

  return (
    <div className="space-y-8">
      {cases.length > 0 ? (
        <section aria-labelledby="your-cases-h" className="space-y-3">
          <h2 id="your-cases-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("yourCases", { n: cases.length })}
          </h2>
          {cases.length > 1 && (
            <div className="flex flex-wrap items-end gap-3" role="search">
              <div className="relative min-w-0 flex-1 basis-56">
                <label htmlFor="case-q" className="sr-only">{t("searchLabel")}</label>
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-ink-3" />
                <input id="case-q" type="search" placeholder={t("searchLabel")} className="min-h-11 w-full rounded-xl border border-line bg-surface py-2 pl-10 pr-3 text-[15px]" value={q} onChange={(e) => setQ(e.target.value)} />
              </div>
              <div>
                <label htmlFor="case-filter" className="mb-1 block text-[13px] font-semibold text-ink-2">{t("filterLabel")}</label>
                <select id="case-filter" className={selectCls} value={filter} onChange={(e) => setFilter(e.target.value as Filter)}>
                  {FILTERS.map((f) => <option key={f} value={f}>{tf(`filter.${f}`)}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="case-sort" className="mb-1 block text-[13px] font-semibold text-ink-2">{t("sortLabel")}</label>
                <select id="case-sort" className={selectCls} value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                  {SORTS.map((o) => <option key={o} value={o}>{tf(`sort.${o}`)}</option>)}
                </select>
              </div>
            </div>
          )}
          {shown.length < cases.length && (
            <p className="text-[13.5px] text-ink-3" aria-live="polite">{tf("showing", { n: shown.length, total: cases.length })}</p>
          )}
          {shown.length === 0 ? (
            <p className="rounded-2xl bg-bg-sunken p-4 text-ink-2">{t("noMatch")}</p>
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2" data-testid="case-list">
              {shown.map((c) => (
                <li key={c.id}>
                  <CaseTile card={c} onOpen={() => select(c.id)} />
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <div className="rounded-2xl border border-dashed border-line bg-bg-sunken p-6">
          <span className="grid size-11 place-items-center rounded-xl bg-teal-100 text-teal-700">
            <FolderIcon className="size-6" />
          </span>
          <p className="mt-3 font-display text-[19px] font-bold">{t("emptyTitle")}</p>
          <p className="mt-1 text-ink-2">{t("emptyBody")}</p>
          <Button asChild className="mt-4">
            <Link href="/chat">
              {t("openChat")}
              <ArrowRightIcon />
            </Link>
          </Button>
        </div>
      )}

      {addCard}

      {notStarted.length > 0 && (
        <section aria-labelledby="start-h" className="space-y-3">
          <h2 id="start-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("startTitle")}
          </h2>
          <p className="text-[14.5px] text-ink-2">{t("startHelp")}</p>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="start-list">
            {notStarted.map((s) => (
              <li key={s.id} className="flex flex-col rounded-[20px] border border-line bg-surface p-5">
                <span className="font-display text-[19px] font-bold leading-tight">{s.name[locale] ?? s.name.en ?? s.id}</span>
                <span className="mt-1 text-[14px] text-ink-3">{s.department[locale] ?? s.department.en}</span>
                <Button
                  variant="secondary"
                  className="mt-4 self-start"
                  disabled={starting === s.id}
                  onClick={() => start(s.id)}
                  aria-label={`${t("trackThis")}: ${s.name[locale] ?? s.name.en ?? s.id}`}
                >
                  {t("trackThis")}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

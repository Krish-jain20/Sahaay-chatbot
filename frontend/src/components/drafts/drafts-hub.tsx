"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DraftBuilder } from "@/components/drafts/draft-builder";
import { DraftIcon } from "@/components/drafts/draft-icons";
import { ArrowRightIcon, SearchIcon, XIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { fetchDraftCatalog, type DraftCard, type DraftCatalog } from "@/lib/api";
import { cn } from "@/lib/utils";

function kindFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get("kind");
}

/** Pick a draft type from searchable, grouped cards, then fill it in. */
export function DraftsHub() {
  const t = useTranslations("drafts");
  const locale = useLocale();
  const [catalog, setCatalog] = useState<DraftCatalog | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("all");
  const [kind, setKind] = useState<string | null>(null);

  const load = useCallback(() => {
    setState("loading");
    fetchDraftCatalog(locale).then((c) => {
      setCatalog(c);
      setState(c ? "ready" : "error");
    });
  }, [locale]);
  useEffect(load, [load]);

  // The chosen type lives in the URL (?kind=) so back, reload and links all work.
  useEffect(() => {
    setKind(kindFromUrl());
    const onPop = () => setKind(kindFromUrl());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const choose = (id: string | null) => {
    window.history.pushState(null, "", id ? `?kind=${id}` : window.location.pathname);
    setKind(id);
    window.scrollTo({ top: 0 });
  };

  const q = query.trim().toLowerCase();
  const visible = useMemo(() => {
    if (!catalog) return [];
    const groupTitle = new Map(catalog.groups.map((g) => [g.id, g.title]));
    return catalog.kinds.filter((k) => {
      if (group !== "all" && k.group !== group) return false;
      if (!q) return true;
      return `${k.title} ${k.blurb} ${k.tags.join(" ")} ${groupTitle.get(k.group) ?? ""}`.toLowerCase().includes(q);
    });
  }, [catalog, group, q]);

  if (state === "loading") {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label={t("searchLabel")}>
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="h-44 animate-pulse rounded-[20px] border border-line bg-bg-sunken motion-reduce:animate-none" />
        ))}
      </div>
    );
  }
  if (state === "error" || !catalog) {
    return (
      <div role="alert" className="space-y-3 rounded-2xl border border-line bg-surface p-5">
        <p>{t("loadFail")}</p>
        <Button variant="secondary" onClick={load}>
          {t("retry")}
        </Button>
      </div>
    );
  }

  const chosen = kind ? catalog.kinds.find((k) => k.id === kind) : undefined;
  if (chosen) return <DraftBuilder key={chosen.id} card={chosen} onBack={() => choose(null)} />;

  const groups = catalog.groups.filter((g) => visible.some((k) => k.group === g.id));
  const sectioned = group === "all" && !q;
  const countIn = (id: string) => catalog.kinds.filter((k) => k.group === id).length;
  const general = catalog.kinds.find((k) => k.id === "complaint");

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="relative max-w-xl">
          <label htmlFor="draft-search" className="sr-only">
            {t("searchLabel")}
          </label>
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-ink-3" />
          <input
            id="draft-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="min-h-12 w-full rounded-full border border-line bg-surface pl-12 pr-12 text-[16px] placeholder:text-ink-3"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label={t("clear")}
              className="absolute right-1.5 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full text-ink-2 hover:bg-bg-sunken"
            >
              <XIcon className="size-5" />
            </button>
          )}
        </div>
        <div role="group" aria-label={t("groupLabel")} className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
          {[{ id: "all", title: t("all"), n: catalog.kinds.length }, ...catalog.groups.map((g) => ({ ...g, n: countIn(g.id) }))].map((g) => (
            <button
              key={g.id}
              type="button"
              aria-pressed={group === g.id}
              onClick={() => setGroup(g.id)}
              className={cn(
                "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full border px-4 text-[14.5px] font-semibold transition-colors",
                group === g.id ? "border-teal-700 bg-teal-700 text-white" : "border-line bg-surface text-ink-2 hover:border-teal-700 hover:text-teal-700",
              )}
            >
              {g.title}
              <span className={cn("text-[12.5px] font-medium", group === g.id ? "text-white/80" : "text-ink-3")}>{g.n}</span>
            </button>
          ))}
        </div>
        <p aria-live="polite" className="text-[13.5px] text-ink-3">
          {t("count", { n: visible.length })}
        </p>
      </div>

      {visible.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line bg-bg-sunken p-6">
          <p className="font-display text-[19px] font-bold">{t("none", { q: query.trim() })}</p>
          <p className="mt-1 text-ink-2">{t("noneHelp")}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => { setQuery(""); setGroup("all"); }}>
              {t("clear")}
            </Button>
            {general && <Button onClick={() => choose(general.id)}>{t("openGeneral")}</Button>}
          </div>
        </div>
      ) : sectioned ? (
        groups.map((g) => (
          <section key={g.id} aria-labelledby={`g-${g.id}`} className="space-y-3">
            <h2 id={`g-${g.id}`} className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
              {g.title}
            </h2>
            <CardGrid cards={visible.filter((k) => k.group === g.id)} onPick={choose} />
          </section>
        ))
      ) : (
        <CardGrid cards={visible} onPick={choose} />
      )}
    </div>
  );
}

function CardGrid({ cards, onPick }: { cards: DraftCard[]; onPick: (id: string) => void }) {
  const t = useTranslations("drafts");
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((c) => (
        <li key={c.id}>
          <button
            type="button"
            data-testid={`draft-${c.id}`}
            onClick={() => onPick(c.id)}
            className="group flex h-full min-h-44 w-full flex-col rounded-[20px] border border-line bg-surface p-5 text-left transition duration-200 hover:-translate-y-0.5 hover:border-teal-700 hover:shadow-[0_10px_24px_rgba(15,76,92,0.12)] motion-reduce:transition-none motion-reduce:hover:translate-y-0"
          >
            <span className="grid size-11 place-items-center rounded-xl bg-teal-100 text-teal-700">
              <DraftIcon name={c.icon} className="size-6" />
            </span>
            <span className="mt-4 block font-display text-[19px] font-bold leading-tight">{c.title}</span>
            <span className="mt-1.5 block text-[14.5px] text-ink-2">{c.blurb}</span>
            <span className="mt-auto flex items-center justify-between gap-2 pt-4 text-[13.5px]">
              <span className="text-ink-3">{t("fieldsCount", { n: c.fields.length })}</span>
              <ArrowRightIcon className="size-4 text-teal-700 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" />
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

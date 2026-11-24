"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { CaseDetail } from "@/components/case/case-detail";
import { CaseTile } from "@/components/case/case-tile";
import { ArrowLeftIcon, ArrowRightIcon, FolderIcon } from "@/components/icons";
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

/** My cases: the services you are tracking, what each one needs next, and where to go to do it. */
export function MyCases() {
  const t = useTranslations("case");
  const locale = useLocale() as "en" | "hi" | "hn";
  const [cases, setCases] = useState<CaseCard[] | null>(null);
  const [services, setServices] = useState<ServiceLite[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [starting, setStarting] = useState<string | null>(null);

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

  const tracked = new Set(cases.map((c) => c.service_id));
  const notStarted = services.filter((s) => !tracked.has(s.id));

  return (
    <div className="space-y-8">
      {cases.length > 0 ? (
        <section aria-labelledby="your-cases-h" className="space-y-3">
          <h2 id="your-cases-h" className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">
            {t("yourCases", { n: cases.length })}
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2" data-testid="case-list">
            {cases.map((c) => (
              <li key={c.id}>
                <CaseTile card={c} onOpen={() => select(c.id)} />
              </li>
            ))}
          </ul>
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

"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { ArrowRightIcon } from "@/components/icons";
import { API_URL } from "@/lib/sse";

interface Card {
  id: string;
  name: string;
  department: string;
}

const SHOWN = 10;

/** Service names come from the data, so the strip and the count never go stale. */
export function PopularServices() {
  const t = useTranslations("home");
  const locale = useLocale();
  const [cards, setCards] = useState<Card[] | null>(null);
  useEffect(() => {
    fetch(`${API_URL}/cards?lang=${locale}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((list: Card[]) => setCards(list))
      .catch(() => setCards(null));
  }, [locale]);
  return (
    <section aria-labelledby="svc-h" className="border-t border-line py-14 lg:py-20">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("services.eyebrow")}</p>
          <h2 id="svc-h" className="mt-3 text-[30px] font-extrabold leading-[1.08] sm:text-[36px]">{t("services.title")}</h2>
          <p className="mt-3 text-[16.5px] text-ink-2" data-testid="scope-banner">
            {cards ? t("scope", { n: cards.length }) : t("scopeNoCount")}
          </p>
        </div>
        <Link href="/compare" className="inline-flex min-h-11 items-center gap-1.5 text-[15px] font-semibold text-teal-700 underline decoration-teal-700/30 underline-offset-4 hover:decoration-teal-700">
          {t("services.all")}
          <ArrowRightIcon className="size-4" />
        </Link>
      </div>
      {cards && (
        <ul className="mt-8 flex flex-wrap gap-2.5" data-testid="popular-services">
          {cards.slice(0, SHOWN).map((c) => (
            <li key={c.id}>
              <Link
                href={`/compare#${c.id}`}
                className="inline-flex min-h-11 items-center rounded-full border border-line bg-surface px-4 text-[15px] text-ink transition-colors hover:border-teal-700 hover:text-teal-700 motion-reduce:transition-none"
              >
                {c.name}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

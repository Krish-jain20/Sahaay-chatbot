"use client";

import { useTranslations } from "next-intl";

import type { GuideCardData } from "@/lib/types";

export function GuideCard({ card }: { card: GuideCardData }) {
  const t = useTranslations("help");
  return (
    <article className="mt-3 space-y-4 rounded-2xl border border-line bg-surface p-4" data-testid="guide-card">
      <header>
        <h2 className="text-[19px] font-bold">{card.title}</h2>
        <p className="text-[15px] text-ink-2">{card.intro}</p>
      </header>
      <ol className="space-y-4">
        {card.points.map((p) => (
          <li key={p.id} data-testid={`guide-${p.id}`}>
            <h3 className="text-[16px] font-semibold">
              {p.heading}{" "}
              <sup className="font-bold text-teal-700" aria-label={t("source", { n: p.source_n })}>[{p.source_n}]</sup>
            </h3>
            <p className="text-[15px] text-ink-2">{p.body}</p>
          </li>
        ))}
      </ol>
      <footer className="border-t border-line pt-3">
        <h3 className="text-[14px] font-semibold text-ink-2">{t("sources")}</h3>
        <ul className="mt-1 space-y-1 text-[14px]">
          {card.citations.map((c) => (
            <li key={c.n}>
              [{c.n}] {c.publisher}:{" "}
              <a href={c.url} target="_blank" rel="noopener noreferrer" className="break-all text-teal-700 underline">
                {c.url}
              </a>{" "}
              <span className="text-ink-3">{c.date_checked ? t("checkedOn", { date: c.date_checked }) : t("notChecked")}</span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[13.5px] text-ink-3">{t("note")}</p>
      </footer>
    </article>
  );
}

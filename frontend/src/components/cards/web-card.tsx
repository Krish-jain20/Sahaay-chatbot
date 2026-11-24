"use client";

import { useTranslations } from "next-intl";

import { AlertIcon } from "@/components/icons";
import type { WebCardData } from "@/lib/types";

/** Shown above an answer that came from a live web search instead of a verified Sahaay record. */
export function WebCard({ card }: { card: WebCardData }) {
  const t = useTranslations("web");
  return (
    <aside className="mt-3 space-y-2 rounded-2xl border border-line bg-surface p-4" data-testid="web-card">
      <p className="inline-flex items-center gap-2 rounded-full bg-marigold-050 px-3 py-1 text-[13.5px] font-semibold text-ink">
        <AlertIcon className="size-4" />
        {card.label}
      </p>
      {card.sources.length > 0 && (
        <>
          <h3 className="text-[14px] font-semibold text-ink-2">{t("sources")}</h3>
          <ul className="space-y-1 text-[14px]">
            {card.sources.map((s) => (
              <li key={s.n}>
                [{s.n}]{" "}
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                  {s.title}
                </a>{" "}
                <span className="text-ink-3">{s.official ? t("official") : t("unofficial")}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="text-[13.5px] text-ink-3">{t("retrieved", { date: card.retrieved_on })}</p>
    </aside>
  );
}

"use client";

import { useTranslations } from "next-intl";

import { AlertIcon, ArrowRightIcon } from "@/components/icons";
import type { CaseCard } from "@/lib/api";

/** One case as a card: same look as the Drafts and Home cards. Progress is the user's own record. */
export function CaseTile({ card, onOpen }: { card: CaseCard; onOpen: () => void }) {
  const t = useTranslations("case");
  const tt = t as unknown as (key: string, values?: Record<string, string | number>) => string;
  const ov = card.overview;
  const pct = Math.round((ov.steps_done / ov.steps_total) * 100);
  return (
    <button
      type="button"
      onClick={onOpen}
      data-testid={`case-${card.service_id}`}
      className="group flex h-full min-h-44 w-full flex-col rounded-[20px] border border-line bg-surface p-5 text-left transition duration-200 hover:-translate-y-0.5 hover:border-teal-700 hover:shadow-[0_10px_24px_rgba(15,76,92,0.12)] motion-reduce:transition-none motion-reduce:hover:translate-y-0"
    >
      <span className="font-display text-[19px] font-bold leading-tight">{card.service_name}</span>
      <span className="mt-0.5 text-[13.5px] text-ink-3">{card.department}</span>

      <span className="mt-4 text-[13.5px] font-semibold text-ink-2">{tt("stepsRecorded", { done: ov.steps_done, total: ov.steps_total })}</span>
      <span aria-hidden className="mt-1.5 block h-2 overflow-hidden rounded-full bg-bg-sunken">
        <span className="block h-full rounded-full bg-teal-700" style={{ width: `${pct}%` }} />
      </span>

      <span className="mt-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("nextAction")}</span>
      <span className="mt-0.5 text-[15px] font-semibold">{tt(`na.${ov.next_action}`)}</span>

      {ov.missing.length > 0 && (
        <span className="mt-2 inline-flex items-start gap-1.5 text-[13.5px] text-warn-700">
          <AlertIcon className="mt-0.5 size-4 shrink-0" />
          {tt("missingCount", { n: ov.missing.length })}
        </span>
      )}

      <span className="mt-auto flex items-center justify-between gap-2 pt-4 text-[13.5px]">
        <span className="text-ink-3">{tt("docsReady", { done: ov.docs_ready, total: ov.docs_total })}</span>
        <ArrowRightIcon className="size-4 text-teal-700 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" />
      </span>
    </button>
  );
}

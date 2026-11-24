"use client";

import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

import { AlertIcon, CheckIcon, HelpIcon, LinkIcon, ShieldCheckIcon, XIcon } from "@/components/icons";
import { ReportButton } from "@/components/cards/report-button";
import type { Citation, RuleResult, ServiceCardData } from "@/lib/types";
import { cn } from "@/lib/utils";

function CiteChip({ n, citations }: { n: number; citations: Citation[] }) {
  const t = useTranslations("card");
  const c = citations.find((x) => x.n === n);
  if (!c) return null;
  return (
    <details className="relative inline-block align-middle">
      <summary
        className="inline-flex size-6 cursor-pointer list-none items-center justify-center rounded-md bg-teal-100 text-[12px] font-bold text-teal-700"
        aria-label={t("source", { n })}
      >
        {n}
      </summary>
      <div className="absolute right-0 z-20 mt-1 w-64 rounded-2xl border border-line bg-surface p-3 text-[14px] shadow-[0_10px_24px_rgba(15,76,92,0.12)]">
        <p className="font-semibold">{c.title}</p>
        <p className="text-ink-3">{c.publisher}</p>
        <a href={c.url} target="_blank" rel="noopener noreferrer" className="break-all text-teal-700 underline">
          {c.url}
        </a>
        <p className="mt-1 text-ink-3">{c.date_checked ? t("checkedOn", { date: c.date_checked }) : t("notChecked")}</p>
      </div>
    </details>
  );
}

function RuleRow({ label, result }: { label: string; result: RuleResult }) {
  const t = useTranslations("card");
  const style = {
    met: { icon: <CheckIcon className="size-4" />, chip: "bg-ok-100 text-ok-700", text: t("met") },
    not_met: { icon: <XIcon className="size-4" />, chip: "bg-bad-100 text-bad-700", text: t("notMet") },
    unknown: { icon: <HelpIcon className="size-4" />, chip: "bg-warn-100 text-warn-700", text: t("unknown") },
  }[result];
  return (
    <li className="flex items-center justify-between gap-3 py-1.5">
      <span className="flex items-center gap-2">
        <span className={cn("inline-flex size-6 shrink-0 items-center justify-center rounded-full", style.chip)}>{style.icon}</span>
        {label}
      </span>
      <span className={cn("rounded-full px-2.5 py-0.5 text-[12.5px] font-semibold", style.chip)}>{style.text}</span>
    </li>
  );
}

export function ServiceCard({ card, citations }: { card: ServiceCardData; citations: Citation[] }) {
  const t = useTranslations("card");
  const format = useFormatter();
  const { service, eligibility, fee_strip: fee } = card;
  const src = citations.find((c) => c.n === service.source_n);
  const verified = service.status === "verified" && !service.stale && src?.date_checked;
  const inr = (v: number | null) =>
    v === null ? t("verifyLocally") : format.number(v, { style: "currency", currency: "INR", maximumFractionDigits: 0 });

  return (
    <article className="animate-rise mt-3 rounded-[20px] border border-line bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-[19px] font-bold">{service.name}</h3>
          <p className="text-[14px] text-ink-3">{service.department}</p>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12.5px] font-semibold",
            verified ? "bg-ok-100 text-ok-700" : "bg-warn-100 text-warn-700",
          )}
        >
          {verified ? <ShieldCheckIcon className="size-4" /> : <AlertIcon className="size-4" />}
          {verified ? t("verified", { date: src!.date_checked! }) : t("verifyLocally")}
          <CiteChip n={service.source_n} citations={citations} />
        </span>
      </div>

      <p className="mt-2 text-[15px] text-ink-2">{service.summary}</p>
      {service.benefit && (
        <p className="mt-2 text-[15px]">
          <span className="font-semibold">{t("benefit")}: </span>
          {service.benefit}
        </p>
      )}

      <h4 className="mt-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-ink-3">{t("eligibility")}</h4>
      <ul className="text-[15px]">
        {eligibility.rules.map((r) => (
          <RuleRow key={r.rule_id} label={r.label} result={r.result} />
        ))}
      </ul>
      {eligibility.exclusions_hit.length > 0 && (
        <div className="mt-2 rounded-2xl bg-bad-100 p-3 text-[15px] text-bad-700">
          <p className="font-semibold">{t("excluded")}</p>
          <ul>
            {eligibility.exclusions_hit.map((x) => (
              <li key={x.id} className="flex items-start gap-2">
                <XIcon className="mt-0.5 size-4 shrink-0" />
                {x.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-[12.5px] text-ink-3">{t("notApproval")}</p>

      {card.prerequisites.length > 0 && (
        <>
          <h4 className="mt-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-ink-3">{t("prerequisites")}</h4>
          <ol className="mt-1 flex flex-wrap items-center gap-2 text-[14px]">
            {[...card.prerequisites.map((p) => p.name), service.name].map((name, i, all) => (
              <li
                key={name}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1",
                  i === all.length - 1 ? "border-teal-700 bg-teal-700 text-white" : "border-line bg-surface",
                )}
              >
                <span className="font-bold">{i + 1}</span>
                {name}
              </li>
            ))}
          </ol>
        </>
      )}

      {card.alternatives.length > 0 && (
        <section aria-labelledby={`alt-${service.id}`}>
          <h4 id={`alt-${service.id}`} className="mt-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-ink-3">
            {t("alternatives")}
          </h4>
          <ul className="mt-1 space-y-1 text-[14px]" data-testid="alternatives">
            {card.alternatives.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{a.name}</span>
                <span className="text-ink-3">{a.verdict === "likely" ? t("altLikely") : t("altIncomplete")}</span>
              </li>
            ))}
          </ul>
          <p className="text-[12.5px] text-ink-3">{t("altHint")}</p>
        </section>
      )}
      <dl className="mt-3 grid grid-cols-3 gap-2 rounded-2xl bg-teal-100 p-3 text-[14px]">
        <div>
          <dt className="text-ink-3">{t("officialFee")}</dt>
          <dd className="font-semibold">{inr(fee.official_fee_inr)}</dd>
        </div>
        <div>
          <dt className="text-ink-3">{t("cscMax")}</dt>
          <dd className="font-semibold">{inr(fee.csc_max_inr)}</dd>
        </div>
        <div>
          <dt className="text-ink-3">{t("processing")}</dt>
          <dd className="font-semibold">
            {fee.processing_days === null ? t("verifyLocally") : t("days", { n: fee.processing_days, type: fee.day_type ?? "other" })}
          </dd>
        </div>
      </dl>

      {card.grievance.length > 0 && (
        <section aria-labelledby={`gr-${service.id}`}>
          <h4 id={`gr-${service.id}`} className="text-[11px] font-semibold uppercase tracking-[0.05em] text-ink-3">
            {t("complain")}
          </h4>
          <ul className="mt-1 space-y-1 text-[14px]" data-testid="grievance-channels">
            {card.grievance.map((g) => (
              <li key={`${g.type}-${g.name}`}>
                {g.url ? (
                  <a href={g.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-700 underline">
                    {g.name}
                  </a>
                ) : (
                  <span className="font-semibold">{g.name}</span>
                )}
                {g.phone && (
                  <>
                    {" "}
                    <a href={`tel:${g.phone.replace(/\s/g, "")}`} className="text-teal-700 underline">{g.phone}</a>
                  </>
                )}{" "}
                <CiteChip n={g.source_n} citations={citations} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-x-4">
        <ReportButton serviceId={service.id} />
        <Link href="/help/scams" className="inline-flex min-h-11 items-center text-[14px] text-teal-700 underline">
          {t("fraudLink")}
        </Link>
      </div>

      {service.official_url && (
        <a
          href={service.official_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex min-h-11 items-center gap-2 font-semibold text-teal-700 underline"
        >
          <LinkIcon className="size-5" />
          {t("openPortal")}
        </a>
      )}
    </article>
  );
}

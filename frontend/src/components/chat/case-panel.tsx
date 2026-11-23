"use client";

import { useFormatter, useTranslations } from "next-intl";

/** Right-hand panel on desktop: the details confirmed so far. (The full case folder is Stage 5.) */
export function CasePanel({ facts, saved }: { facts: Record<string, unknown>; saved: boolean }) {
  const t = useTranslations("panel");
  const tf = useTranslations("facts");
  const format = useFormatter();
  const entries = Object.entries(facts);

  function show(key: string, v: unknown): string {
    if (typeof v === "boolean") return v ? t("yes") : t("no");
    if (key === "annual_family_income_inr" && typeof v === "number") {
      return format.number(v, { style: "currency", currency: "INR", maximumFractionDigits: 0 });
    }
    return String(v);
  }

  return (
    <aside aria-label={t("title")} className="sticky top-0 hidden h-dvh overflow-y-auto border-l border-line bg-bg-panel p-4 xl:block">
      <h2 className="text-[19px] font-bold">{t("title")}</h2>
      {entries.length === 0 ? (
        <p className="mt-2 text-[15px] text-ink-3">{t("empty")}</p>
      ) : (
        <>
          <dl className="mt-3 space-y-2 text-[15px]">
            {entries.map(([k, v]) => (
              <div key={k} className="rounded-2xl border border-line bg-surface px-3 py-2">
                <dt className="text-[12.5px] text-ink-3">{tf.has(k) ? tf(k) : k}</dt>
                <dd className="font-semibold">{show(k, v)}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-[13px] text-ink-3">{saved ? t("saved") : t("notSaved")}</p>
        </>
      )}
    </aside>
  );
}

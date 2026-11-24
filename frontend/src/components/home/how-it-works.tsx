import { useTranslations } from "next-intl";

export function HowItWorks() {
  const t = useTranslations("home.how");
  return (
    <section aria-labelledby="how-h" className="border-t border-line py-14 lg:py-20">
      <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("eyebrow")}</p>
          <h2 id="how-h" className="mt-3 text-[30px] font-extrabold leading-[1.08] sm:text-[36px]">{t("title")}</h2>
        </div>
        <ol className="divide-y divide-line">
          {(["1", "2", "3"] as const).map((n) => (
            <li key={n} className="grid grid-cols-[3.25rem_1fr] gap-4 py-6 first:pt-0 last:pb-0 sm:grid-cols-[4.5rem_1fr]">
              <span className="font-display text-[44px] font-extrabold leading-none text-marigold-500 sm:text-[56px]" aria-hidden="true">
                {n}
              </span>
              <div>
                <h3 className="text-[20px] font-bold">{t(`s${n}t`)}</h3>
                <p className="mt-1.5 max-w-[34rem] text-[16px] text-ink-2">{t(`s${n}b`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

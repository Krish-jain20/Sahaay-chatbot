import { useTranslations } from "next-intl";

import { AlertIcon, LockIcon, ShieldCheckIcon } from "@/components/icons";

const POINTS = [
  { id: "sources", Icon: ShieldCheckIcon },
  { id: "files", Icon: LockIcon },
  { id: "notOfficial", Icon: AlertIcon },
] as const;

export function Trust() {
  const t = useTranslations("home.trust");
  return (
    <section aria-labelledby="trust-h" className="py-14 lg:py-20">
      <div className="rounded-[28px] bg-teal-700 px-6 py-10 text-white sm:px-10 lg:px-14 lg:py-14">
        <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-050">{t("eyebrow")}</p>
        <h2 id="trust-h" className="mt-3 max-w-2xl text-[30px] font-extrabold leading-[1.08] text-white sm:text-[36px]">{t("title")}</h2>
        <ul className="mt-9 grid gap-8 md:grid-cols-3 md:gap-10">
          {POINTS.map(({ id, Icon }) => (
            <li key={id}>
              <span className="grid size-11 place-items-center rounded-xl bg-white/12 text-marigold-500">
                <Icon className="size-6" />
              </span>
              <h3 className="mt-4 text-[19px] font-bold text-white">{t(`${id}T`)}</h3>
              <p className="mt-1.5 text-[15.5px] leading-[1.55] text-white/85">{t(`${id}B`)}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

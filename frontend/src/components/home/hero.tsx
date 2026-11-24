import Link from "next/link";
import { useTranslations } from "next-intl";

import { ChatPreview } from "@/components/home/chat-preview";
import { CheckIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";

export function Hero() {
  const t = useTranslations("home");
  return (
    <section aria-labelledby="home-h1" className="grid items-center gap-10 py-10 lg:grid-cols-[1.08fr_0.92fr] lg:gap-14 lg:py-16">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("eyebrow")}</p>
        <h1
          id="home-h1"
          className="mt-4 text-[40px] font-extrabold leading-[1.04] tracking-[-0.03em] text-ink sm:text-[52px] lg:text-[58px]"
        >
          {t("headline")}
        </h1>
        <p className="mt-5 max-w-[34rem] text-[18px] leading-[1.55] text-ink-2">{t("sub")}</p>
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <Button asChild variant="accent" className="min-h-12 px-7 text-[16px]">
            <Link href="/chat">{t("start")}</Link>
          </Button>
          <Link href="/compare" className="inline-flex min-h-11 items-center text-[15.5px] font-semibold text-teal-700 underline decoration-teal-700/30 underline-offset-4 hover:decoration-teal-700">
            {t("browse")}
          </Link>
        </div>
        <ul className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-[14px] text-ink-2">
          {(["point1", "point2", "point3"] as const).map((k) => (
            <li key={k} className="inline-flex items-center gap-2">
              <CheckIcon className="size-4 text-teal-700" />
              {t(k)}
            </li>
          ))}
        </ul>
      </div>
      <ChatPreview />
    </section>
  );
}

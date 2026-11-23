import Link from "next/link";
import { useTranslations } from "next-intl";

import { Disclaimer, TopBar } from "@/components/top-bar";
import { Button } from "@/components/ui/button";

export default function Home() {
  const t = useTranslations();
  return (
    <>
      <TopBar />
      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10">
        <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("common.tagline")}</p>
        <h1 className="text-[31px] font-extrabold sm:text-[34px]">{t("home.headline")}</h1>
        <p className="text-[17px] text-ink-2">{t("home.sub")}</p>
        <div>
          <Button asChild variant="accent">
            <Link href="/chat">{t("home.start")}</Link>
          </Button>
        </div>
        <p className="rounded-2xl bg-teal-100 px-4 py-3 text-[15px] text-ink-2">{t("home.scope")}</p>
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </>
  );
}

import Link from "next/link";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/app-shell";
import { Disclaimer } from "@/components/top-bar";
import { Button } from "@/components/ui/button";

export default function Home() {
  const t = useTranslations();
  return (
    <AppShell>
      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10">
        <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("common.tagline")}</p>
        <h1 className="text-[31px] font-extrabold sm:text-[34px]">{t("home.headline")}</h1>
        <p className="text-[17px] text-ink-2">{t("home.sub")}</p>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="accent">
            <Link href="/chat">{t("home.start")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/compare">{t("compare.link")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/case">{t("nav.case")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/documents">{t("nav.documents")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/drafts">{t("nav.drafts")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/forms">{t("nav.forms")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/help/complaints">{t("nav.help")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/help/scams">{t("nav.safe")}</Link>
          </Button>
        </div>
        <p className="rounded-2xl bg-teal-100 px-4 py-3 text-[15px] text-ink-2">{t("home.scope")}</p>
        <p className="text-center text-[13.5px]">
          <Link href="/privacy" className="inline-flex min-h-11 items-center text-teal-700 underline">
            {t("nav.privacy")}
          </Link>
        </p>
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

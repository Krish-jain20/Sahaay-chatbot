import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { CompareTable } from "@/components/compare/compare-table";
import { Disclaimer } from "@/components/top-bar";

export default async function ComparePage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-5xl space-y-4 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("compare.title")}</h1>
        <CompareTable />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { MyCases } from "@/components/case/my-cases";
import { Disclaimer } from "@/components/top-bar";

export default async function CasePage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-4xl space-y-4 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("case.title")}</h1>
        <p className="text-ink-2">{t("case.sub")}</p>
        <MyCases />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

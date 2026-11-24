import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { HelpHub } from "@/components/help/help-hub";
import { Disclaimer } from "@/components/top-bar";

export default async function HelpPage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("nav.help")}</h1>
        <HelpHub />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

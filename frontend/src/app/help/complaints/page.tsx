import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { GuidePage } from "@/components/help/guide-page";
import { Disclaimer } from "@/components/top-bar";

export default async function ComplaintsHelpPage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
        <h1 className="sr-only">{t("nav.help")}</h1>
        <GuidePage topic="complaints" />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { DraftsHub } from "@/components/drafts/drafts-hub";
import { Disclaimer } from "@/components/top-bar";

export default async function DraftsPage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <div className="max-w-2xl">
          <h1 className="text-[31px] font-extrabold">{t("drafts.title")}</h1>
          <p className="mt-2 text-ink-2">{t("drafts.sub")}</p>
        </div>
        <DraftsHub />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { DocumentCheck } from "@/components/documents/document-check";
import { Disclaimer } from "@/components/top-bar";

export default async function DocumentsPage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("docs.title")}</h1>
        <p className="text-ink-2">{t("docs.sub")}</p>
        <DocumentCheck />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

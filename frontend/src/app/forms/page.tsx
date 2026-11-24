import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { FormsHub } from "@/components/forms/forms-hub";
import { Disclaimer } from "@/components/top-bar";

export default async function FormsPage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("forms.title")}</h1>
        <FormsHub />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

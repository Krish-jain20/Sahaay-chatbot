import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { FormFiller } from "@/components/forms/form-filler";
import { Disclaimer } from "@/components/top-bar";

export default async function FormsPage() {
  const t = await getTranslations();
  return (
    <AppShell wide>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("forms.title")}</h1>
        <p className="text-ink-2">{t("forms.sub")}</p>
        <FormFiller />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

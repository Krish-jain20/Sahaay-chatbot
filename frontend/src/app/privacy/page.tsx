import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app-shell";
import { AccountPanel } from "@/components/privacy/account-panel";
import { MyDataPanel } from "@/components/privacy/privacy-page";
import { Disclaimer } from "@/components/top-bar";

export default async function PrivacyPage() {
  const t = await getTranslations();
  const list = (keys: string[]) => (
    <ul className="list-disc space-y-1 pl-5 text-[15px] text-ink-2">
      {keys.map((k) => (
        <li key={k}>{t(`privacy.${k}`)}</li>
      ))}
    </ul>
  );
  return (
    <AppShell wide>
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        <h1 className="text-[31px] font-extrabold">{t("privacy.title")}</h1>
        <p className="text-ink-2">{t("privacy.sub")}</p>
        <section className="space-y-2">
          <h2 className="text-[17px] font-bold">{t("privacy.keepTitle")}</h2>
          {list(["keep1", "keep2", "keep3"])}
        </section>
        <section className="space-y-2">
          <h2 className="text-[17px] font-bold">{t("privacy.neverTitle")}</h2>
          {list(["never1", "never2", "never3"])}
        </section>
        <p className="rounded-xl bg-marigold-050 px-4 py-3 text-[14px] text-ink-2">{t("privacy.modelNote")}</p>
        <p className="text-[14px] text-ink-3">{t("privacy.reports")}</p>
        <AccountPanel />
        <MyDataPanel />
        <Disclaimer text={t("common.disclaimer")} />
      </main>
    </AppShell>
  );
}

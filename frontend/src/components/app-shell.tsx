import { getTranslations } from "next-intl/server";

import { LanguageSwitch } from "@/components/language-switch";
import { Logo } from "@/components/logo";
import { NavLink } from "@/components/nav-link";
import { TopBar } from "@/components/top-bar";

/**
 * App shell (docs/DESIGN.md §5). From 1200px: left nav (252px) | page. The chat page adds the
 * 352px case panel on its own. Below 1200px the nav is replaced by the top bar.
 */
export async function AppShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const t = await getTranslations();
  return (
    <div className="xl:grid xl:min-h-dvh xl:grid-cols-[252px_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh flex-col gap-6 border-r border-line bg-bg-sunken p-4 xl:flex">
        <Logo />
        <nav aria-label={t("nav.menu")} className="flex flex-col gap-1">
          <NavLink href="/">{t("nav.home")}</NavLink>
          <NavLink href="/chat">{t("nav.chat")}</NavLink>
          <NavLink href="/compare">{t("nav.compare")}</NavLink>
          <NavLink href="/case">{t("nav.case")}</NavLink>
          <NavLink href="/documents">{t("nav.documents")}</NavLink>
          <NavLink href="/drafts">{t("nav.drafts")}</NavLink>
          <NavLink href="/forms">{t("nav.forms")}</NavLink>
          <NavLink href="/help/complaints">{t("nav.help")}</NavLink>
          <NavLink href="/help/scams">{t("nav.safe")}</NavLink>
          <NavLink href="/privacy">{t("nav.privacy")}</NavLink>
        </nav>
        <div className="mt-auto space-y-3">
          <LanguageSwitch />
          <p className="text-[12.5px] text-ink-3">{t("common.disclaimer")}</p>
        </div>
      </aside>
      <div className="min-w-0">
        <div className="xl:hidden">
          <TopBar wide={wide} />
        </div>
        {children}
      </div>
    </div>
  );
}

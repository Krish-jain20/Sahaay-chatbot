import Link from "next/link";
import { useTranslations } from "next-intl";

import { Logo } from "@/components/logo";

const GROUPS = [
  { id: "ask", links: [["/chat", "chat"], ["/compare", "compare"], ["/help", "help"]] },
  { id: "prepare", links: [["/documents", "documents"], ["/drafts", "drafts"], ["/forms", "forms"], ["/case", "case"]] },
] as const;

export function SiteFooter() {
  const t = useTranslations();
  return (
    <footer className="border-t border-line py-10">
      <div className="grid gap-8 md:grid-cols-[1.4fr_1fr_1fr_auto]">
        <div className="max-w-xs">
          <Logo />
          <p className="mt-2 text-[14.5px] text-ink-2">{t("common.tagline")}</p>
        </div>
        {GROUPS.map((g) => (
          <nav key={g.id} aria-label={t(`home.footer.${g.id}`)}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-ink-3">{t(`home.footer.${g.id}`)}</p>
            <ul className="mt-2">
              {g.links.map(([href, key]) => (
                <li key={href}>
                  <Link href={href} className="inline-flex min-h-11 min-w-11 items-center text-[15px] text-ink-2 hover:text-teal-700 hover:underline">
                    {t(`nav.${key}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-ink-3">{t("home.footer.about")}</p>
          <Link href="/privacy" className="inline-flex min-h-11 min-w-11 items-center text-[15px] text-ink-2 hover:text-teal-700 hover:underline">
            {t("nav.privacy")}
          </Link>
        </div>
      </div>
      <p className="mt-8 border-t border-line pt-5 text-[13px] text-ink-3">{t("common.disclaimer")}</p>
    </footer>
  );
}

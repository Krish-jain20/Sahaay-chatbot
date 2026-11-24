"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { LOCALE_COOKIE, locales, type Locale } from "@/i18n/config";
import { cn } from "@/lib/utils";

const LABELS: Record<Locale, string> = { en: "EN", hi: "हिंदी", hn: "Hinglish" };

export function LanguageSwitch() {
  const t = useTranslations("common");
  const current = useLocale() as Locale;
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function choose(locale: Locale) {
    document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; samesite=lax`;
    startTransition(() => router.refresh());
  }

  return (
    <div role="group" aria-label={t("language")} className="inline-flex rounded-full border border-line bg-surface p-1" aria-busy={pending}>
      {locales.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => choose(l)}
          aria-pressed={l === current}
          className={cn(
            "min-h-11 min-w-11 rounded-full px-3 text-sm font-semibold",
            l === current ? "bg-teal-700 text-white" : "text-ink-2 hover:bg-bg-sunken",
          )}
        >
          {LABELS[l]}
        </button>
      ))}
    </div>
  );
}

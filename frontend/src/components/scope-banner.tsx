"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { API_URL } from "@/lib/sse";

/** Home banner. The service count comes from the data, so it never goes stale; without it the text has no number. */
export function ScopeBanner() {
  const t = useTranslations("home");
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    fetch(`${API_URL}/cards`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((list: unknown[]) => setCount(list.length))
      .catch(() => setCount(null));
  }, []);
  return (
    <p className="rounded-2xl bg-teal-100 px-4 py-3 text-[15px] text-ink-2" data-testid="scope-banner">
      {count ? t("scope", { n: count }) : t("scopeNoCount")}
    </p>
  );
}

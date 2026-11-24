"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { GuideCard } from "@/components/cards/guide-card";
import { loadGuidance } from "@/lib/api";
import type { GuideCardData } from "@/lib/types";

export function GuidePage({ topic }: { topic: string }) {
  const t = useTranslations("help");
  const locale = useLocale();
  const [card, setCard] = useState<GuideCardData | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    loadGuidance(topic, locale).then((c) => (c ? setCard(c) : setFailed(true)));
  }, [topic, locale]);
  if (failed) return <p role="alert" className="text-bad-700">{t("error")}</p>;
  if (!card) return <p className="text-ink-2">{t("loading")}</p>;
  return <GuideCard card={card} />;
}

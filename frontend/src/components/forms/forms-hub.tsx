"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { AnyForm } from "@/components/forms/any-form";
import { FormFiller } from "@/components/forms/form-filler";
import { cn } from "@/lib/utils";

/** Upload any form, or use the ready Delhi income certificate form. */
export function FormsHub() {
  const t = useTranslations("forms");
  const [mode, setMode] = useState<"any" | "preset">("any");
  const tab = (id: "any" | "preset", label: string) => (
    <button
      type="button"
      aria-pressed={mode === id}
      onClick={() => setMode(id)}
      className={cn(
        "min-h-11 rounded-full border px-4 text-[15px] font-semibold",
        mode === id ? "border-teal-700 bg-teal-700 text-white" : "border-line bg-surface text-ink-2",
      )}
    >
      {label}
    </button>
  );
  return (
    <div className="space-y-5">
      <div role="group" aria-label={t("modeLabel")} className="flex flex-wrap gap-2">
        {tab("any", t("tabAny"))}
        {tab("preset", t("tabPreset"))}
      </div>
      {mode === "any" ? <AnyForm /> : (
        <>
          <p className="text-ink-2">{t("sub")}</p>
          <FormFiller />
        </>
      )}
    </div>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { reportIncorrect } from "@/lib/api";

export function ReportButton({ serviceId }: { serviceId: string }) {
  const t = useTranslations("report");
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  if (state === "sent") return <p className="mt-3 text-[14px] text-ok-700" role="status">{t("thanks")}</p>;

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="mt-3 inline-flex min-h-11 items-center text-[14px] font-semibold text-ink-2 underline">
        {t("button")}
      </button>
    );
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setState("sending");
    setState((await reportIncorrect(serviceId, note.trim())) ? "sent" : "error");
  }

  return (
    <form onSubmit={send} className="mt-3 space-y-2 rounded-2xl bg-bg-sunken p-3">
      <label htmlFor={`report-${serviceId}`} className="block text-[14px] font-semibold">
        {t("label")}
      </label>
      <textarea
        id={`report-${serviceId}`}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        maxLength={1000}
        rows={3}
        className="w-full rounded-xl border border-line bg-surface p-2"
      />
      <p className="text-[12.5px] text-ink-3">{t("hint")}</p>
      <div className="flex gap-2">
        <Button type="submit" disabled={note.trim().length < 3 || state === "sending"}>
          {t("send")}
        </Button>
        <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}

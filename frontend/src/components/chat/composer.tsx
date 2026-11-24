"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { SendIcon, StopIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";

const MAX_ROWS_PX = 140;

/** Message box: Enter sends, Shift+Enter adds a line, it grows up to a few lines, and stays at the bottom. */
export function Composer({
  value,
  onChange,
  onSend,
  onStop,
  busy,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
  busy: boolean;
}) {
  const t = useTranslations("chat");
  const tc = useTranslations("common");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_ROWS_PX)}px`;
  }, [value]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
      className="sticky bottom-0 bg-bg pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2"
    >
      <div data-focus-ring className="flex items-end gap-2 rounded-3xl border border-line bg-surface p-1.5 pl-4 focus-within:border-teal-700 focus-within:ring-[3px] focus-within:ring-teal-700/30">
        <label htmlFor="chat-input" className="sr-only">
          {t("placeholder")}
        </label>
        <textarea
          id="chat-input"
          ref={ref}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends; Shift+Enter is a new line; never send while an IME is composing (Hindi typing).
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              if (!busy) onSend();
            }
          }}
          placeholder={t("placeholder")}
          aria-describedby="composer-hint"
          className="max-h-[140px] min-h-11 flex-1 resize-none bg-transparent py-2.5 text-[16px] leading-6 outline-none focus-visible:outline-none! placeholder:text-ink-3"
          autoComplete="off"
        />
        {busy ? (
          <Button type="button" size="icon" variant="secondary" onClick={onStop} aria-label={t("stop")}>
            <StopIcon />
          </Button>
        ) : (
          <Button type="submit" size="icon" variant="accent" aria-label={t("send")} disabled={!value.trim()}>
            <SendIcon />
          </Button>
        )}
      </div>
      <p id="composer-hint" className="mt-1.5 hidden text-center text-[12px] text-ink-3 sm:block">
        {t("hint")}
      </p>
      <p className="mt-1.5 text-center text-[12.5px] text-ink-3">{tc("disclaimer")}</p>
    </form>
  );
}

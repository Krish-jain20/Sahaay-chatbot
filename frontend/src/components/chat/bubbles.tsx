"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { CheckIcon } from "@/components/icons";
import type { StatusPill } from "@/lib/types";

/** Sahaay's mark (open arch with a marigold dot) in a round badge. Decorative: the name is in the text. */
export function Avatar({ className = "size-8" }: { className?: string }) {
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-full bg-teal-100 ${className}`} aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 32 32">
        <path d="M5 22V16a11 11 0 0 1 22 0v6" fill="none" stroke="var(--teal-700)" strokeWidth="4" strokeLinecap="round" />
        <circle cx="16" cy="26" r="3" fill="var(--marigold-500)" />
      </svg>
    </span>
  );
}

export function UserBubble({ text }: { text: string }) {
  const t = useTranslations("chat");
  return (
    <div className="flex justify-end" data-testid="user-msg">
      <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-[20px_20px_6px_20px] bg-teal-700 px-4 py-2.5 text-white sm:max-w-[75%]">
        <span className="sr-only">{t("you")}: </span>
        {text}
      </p>
    </div>
  );
}

function TypingDots() {
  const t = useTranslations("chat");
  return (
    <span className="inline-flex items-center gap-1 py-1" role="status">
      <span className="sr-only">{t("typing")}</span>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          aria-hidden="true"
          className="size-2 animate-bounce rounded-full bg-teal-700/60"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}

/** A Sahaay reply: avatar, the bubble (step chips, text, note, typing dots), then cards and chips under it. */
export function BotBubble({
  statuses,
  text,
  note,
  streaming,
  children,
}: {
  statuses: StatusPill[];
  text: string;
  note?: string;
  streaming: boolean;
  children?: ReactNode;
}) {
  const t = useTranslations("chat");
  const showBubble = statuses.length > 0 || text || note || streaming;
  return (
    <div className="flex items-start gap-2.5" data-testid="bot-msg">
      <Avatar />
      <div className="min-w-0 max-w-[92%] flex-1 sm:max-w-[85%]">
        {showBubble && (
          <div className="rounded-[20px_20px_20px_6px] border border-line bg-surface px-4 py-3">
            <span className="sr-only">Sahaay: </span>
            {statuses.length > 0 && (
              <ul className={`flex flex-wrap gap-2 ${text || note ? "mb-2" : ""}`} aria-label={t("steps")}>
                {statuses.map((s) => (
                  <li key={s.id} className="animate-rise inline-flex items-center gap-1.5 rounded-full bg-bg-sunken px-3 py-1 text-[13px] text-ink-2">
                    {s.state === "done" ? (
                      <CheckIcon className="size-3.5 text-ok-500" />
                    ) : (
                      <span className="animate-spin-slow inline-block size-3.5 rounded-full border-2 border-teal-700 border-t-transparent" aria-hidden="true" />
                    )}
                    {s.label}
                  </li>
                ))}
              </ul>
            )}
            {text && <p className="whitespace-pre-wrap break-words">{text}</p>}
            {note && <p className="text-[14px] text-ink-3">{note}</p>}
            {streaming && !text && !note && <TypingDots />}
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

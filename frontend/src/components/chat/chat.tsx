"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { ServiceCard } from "@/components/cards/service-card";
import { CheckIcon, SendIcon, StopIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { API_URL, readSse } from "@/lib/sse";
import { getAccessToken } from "@/lib/supabase";
import type { Chip, Citation, ServiceCardData, StatusPill } from "@/lib/types";

interface BotMsg {
  role: "bot";
  text: string;
  statuses: StatusPill[];
  card?: ServiceCardData;
  citations: Citation[];
  chips: Chip[];
  streaming: boolean;
  note?: string;
}
interface UserMsg {
  role: "user";
  text: string;
}
type Msg = BotMsg | UserMsg;

export function Chat() {
  const t = useTranslations("chat");
  const tc = useTranslations("common");
  const locale = useLocale();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [facts, setFacts] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const lastQuestion = useRef("");
  const streamId = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void getAccessToken(); // sign in as a guest as soon as the chat opens
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  function patchBot(fn: (m: BotMsg) => BotMsg) {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last?.role === "bot") next[next.length - 1] = fn(last);
      return next;
    });
  }

  async function ask(question: string, shown: string, confirmed: Record<string, unknown>) {
    if (busy) return;
    lastQuestion.current = question;
    const id = crypto.randomUUID();
    streamId.current = id;
    abort.current = new AbortController();
    setBusy(true);
    setMessages((prev) => [
      ...prev.map((m) => (m.role === "bot" ? { ...m, chips: [] } : m)),
      { role: "user", text: shown },
      { role: "bot", text: "", statuses: [], citations: [], chips: [], streaming: true },
    ]);
    try {
      const token = await getAccessToken();
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ message: question, language: locale, confirmed_facts: confirmed, stream_id: id }),
        signal: abort.current.signal,
      });
      if (!res.ok) throw new Error(String(res.status));
      for await (const { event, data } of readSse(res)) {
        if (event === "status") {
          const s = data as StatusPill;
          if (s.id === "stream") continue;
          patchBot((m) => ({ ...m, statuses: [...m.statuses.filter((x) => x.id !== s.id), s] }));
        } else if (event === "token") {
          const piece = (data as { text: string }).text;
          patchBot((m) => ({ ...m, text: m.text + piece }));
        } else if (event === "card") {
          patchBot((m) => ({ ...m, card: data as ServiceCardData }));
        } else if (event === "citation") {
          patchBot((m) => ({ ...m, citations: [...m.citations, data as Citation] }));
        } else if (event === "chips") {
          patchBot((m) => ({ ...m, chips: (data as { chips: Chip[] }).chips }));
        } else if (event === "error") {
          patchBot((m) => ({ ...m, note: (data as { message: string }).message }));
        } else if (event === "done" && (data as { stopped?: boolean }).stopped) {
          patchBot((m) => ({ ...m, note: t("stopped") }));
        }
      }
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      patchBot((m) => ({ ...m, note: aborted ? t("stopped") : t("error") }));
    } finally {
      patchBot((m) => ({ ...m, streaming: false }));
      setBusy(false);
      abort.current = null;
    }
  }

  async function stop() {
    const id = streamId.current;
    abort.current?.abort();
    if (id) {
      const token = await getAccessToken();
      await fetch(`${API_URL}/chat/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ stream_id: id }),
      }).catch(() => undefined);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setInput("");
    void ask(q, q, facts);
  }

  function pickChip(chip: Chip) {
    const next = { ...facts, ...chip.confirm };
    setFacts(next);
    void ask(lastQuestion.current, chip.label, next);
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-57px)] max-w-3xl flex-col px-4">
      <div className="flex-1 space-y-4 py-6" aria-live="polite">
        {messages.length === 0 && (
          <div className="space-y-3 text-center text-ink-2">
            <p>{t("empty")}</p>
            <div className="flex flex-col items-center gap-2">
              {(["suggestion", "suggestion2", "suggestion3"] as const).map((k) => (
                <Button key={k} variant="chip" className="whitespace-normal text-left" onClick={() => void ask(t(k), t(k), facts)}>
                  {t(k)}
                </Button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[78%] rounded-[20px_20px_6px_20px] bg-teal-700 px-4 py-2.5 text-white">{m.text}</p>
            </div>
          ) : (
            <div key={i} className="max-w-[92%]">
              {m.statuses.length > 0 && (
                <ul className="mb-2 flex flex-wrap gap-2" aria-label="status">
                  {m.statuses.map((s) => (
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
              {(m.text || m.note) && (
                <div className="rounded-[20px_20px_20px_6px] border border-line bg-surface px-4 py-3">
                  {m.text && <p className="whitespace-pre-wrap">{m.text}</p>}
                  {m.note && <p className="text-[14px] text-ink-3">{m.note}</p>}
                </div>
              )}
              {m.card && <ServiceCard card={m.card} citations={m.citations} />}
              {m.chips.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {m.chips.map((c) => (
                    <Button key={c.label} variant="chip" onClick={() => pickChip(c)} disabled={busy}>
                      {c.label}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
        <div ref={bottom} />
      </div>

      <form onSubmit={submit} className="sticky bottom-0 bg-bg pb-3 pt-2">
        <div className="flex items-center gap-2 rounded-full border border-line bg-surface p-1.5 pl-4">
          <label htmlFor="chat-input" className="sr-only">
            {t("placeholder")}
          </label>
          <input
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t("placeholder")}
            className="min-h-11 flex-1 bg-transparent outline-none placeholder:text-ink-3"
            autoComplete="off"
          />
          {busy ? (
            <Button type="button" size="icon" variant="secondary" onClick={() => void stop()} aria-label={t("stop")}>
              <StopIcon />
            </Button>
          ) : (
            <Button type="submit" size="icon" variant="accent" aria-label={t("send")} disabled={!input.trim()}>
              <SendIcon />
            </Button>
          )}
        </div>
        <p className="mt-2 text-center text-[12.5px] text-ink-3">{tc("disclaimer")}</p>
      </form>
    </div>
  );
}

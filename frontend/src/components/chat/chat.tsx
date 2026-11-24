"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { CasePanel } from "@/components/chat/case-panel";
import { GuideCard } from "@/components/cards/guide-card";
import { ServiceCard } from "@/components/cards/service-card";
import { WebCard } from "@/components/cards/web-card";
import { Avatar, BotBubble, UserBubble } from "@/components/chat/bubbles";
import { Composer } from "@/components/chat/composer";
import { Button } from "@/components/ui/button";
import { API_URL, readSse } from "@/lib/sse";
import { deleteMyData, loadFacts, saveFacts } from "@/lib/api";
import { getAccessToken } from "@/lib/supabase";
import type { Chip, Citation, GuideCardData, ServiceCardData, StatusPill, WebCardData } from "@/lib/types";

interface BotMsg {
  role: "bot";
  text: string;
  statuses: StatusPill[];
  card?: ServiceCardData | GuideCardData | WebCardData;
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

const SUGGESTIONS = ["suggestion", "suggestion2", "suggestion3", "suggestion4", "suggestion5", "suggestion6"] as const;

export function Chat() {
  const t = useTranslations("chat");
  const locale = useLocale();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [facts, setFacts] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState<"unknown" | "asking" | "yes" | "no">("unknown");
  const [info, setInfo] = useState<string | null>(null);
  const tp = useTranslations("consent");
  const lastQuestion = useRef("");
  const streamId = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Sign in as a guest on open, then restore details the user chose to save earlier.
    void (async () => {
      await getAccessToken();
      let remembered = false;
      try {
        remembered = localStorage.getItem("sahaay_consent") === "yes";
      } catch {}
      if (remembered) setConsent("yes");
      const saved = await loadFacts();
      if (Object.keys(saved).length) {
        setFacts(saved);
        setConsent("yes");
        setInfo(tp("welcome"));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
          patchBot((m) => ({ ...m, card: data as ServiceCardData | GuideCardData | WebCardData }));
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

  function submit() {
    const q = input.trim();
    if (!q) return;
    setInput("");
    void ask(q, q, facts);
  }

  async function newChat() {
    if (busy) await stop();
    setMessages([]);
    setInput("");
  }

  async function answerConsent(yes: boolean) {
    try {
      localStorage.setItem("sahaay_consent", yes ? "yes" : "no");
    } catch {}
    setConsent(yes ? "yes" : "no");
    if (yes) {
      await saveFacts(facts);
      setInfo(tp("saved"));
    }
  }

  async function removeMyData() {
    if (await deleteMyData()) {
      try {
        localStorage.removeItem("sahaay_consent");
      } catch {}
      setFacts({});
      setConsent("unknown");
      setInfo(tp("deleted"));
    }
  }

  function pickChip(chip: Chip) {
    const next = { ...facts, ...chip.confirm };
    setFacts(next);
    if (consent === "yes") void saveFacts(chip.confirm);
    else if (consent === "unknown") setConsent("asking");
    void ask(lastQuestion.current, chip.label, next);
  }

  const asked = new Set(messages.filter((m) => m.role === "user").map((m) => m.text));
  const last = messages[messages.length - 1];
  const followUps =
    last?.role === "bot" && !last.streaming && last.chips.length === 0
      ? SUGGESTIONS.map((k) => t(k)).filter((q) => !asked.has(q)).slice(0, 3)
      : [];

  return (
    <div className="xl:grid xl:grid-cols-[minmax(0,1fr)_352px]">
      <div className="mx-auto flex min-h-[calc(100dvh-57px)] w-full max-w-3xl flex-col px-4 xl:min-h-dvh">
        <div className="sticky top-0 z-[5] flex items-center justify-between gap-3 bg-bg py-2">
          <div className="flex items-center gap-2.5">
            <Avatar className="size-9" />
            <div className="leading-tight">
              <p className="font-display text-[17px] font-bold text-ink">Sahaay</p>
              <p className="text-[12.5px] text-ink-3">{t("assistantLabel")}</p>
            </div>
          </div>
          {messages.length > 0 && (
            <Button type="button" variant="secondary" onClick={() => void newChat()}>
              {t("newChat")}
            </Button>
          )}
        </div>

        <div className="flex-1 space-y-4 py-4" role="log" aria-live="polite" aria-label={t("log")}>
          {messages.length === 0 && (
            <div className="flex flex-col items-center gap-4 pt-6 text-center" data-testid="chat-empty">
              <Avatar className="size-14" />
              <p className="max-w-xl text-ink-2">{t("empty")}</p>
              <div className="grid w-full max-w-2xl gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((k) => (
                  <Button key={k} variant="chip" className="h-auto justify-start whitespace-normal py-2.5 text-left" onClick={() => void ask(t(k), t(k), facts)}>
                    {t(k)}
                  </Button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <UserBubble key={i} text={m.text} />
            ) : (
              <BotBubble key={i} statuses={m.statuses} text={m.text} note={m.note} streaming={m.streaming}>
                {m.card?.type === "service" && <ServiceCard card={m.card} citations={m.citations} />}
                {m.card?.type === "guide" && <GuideCard card={m.card} />}
                {m.card?.type === "web" && <WebCard card={m.card} />}
                {m.chips.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {m.chips.map((c) => (
                      <Button key={c.label} variant="chip" onClick={() => pickChip(c)} disabled={busy}>
                        {c.label}
                      </Button>
                    ))}
                  </div>
                )}
              </BotBubble>
            ),
          )}
          {followUps.length > 0 && (
            <div className="pl-[42px]" data-testid="follow-ups">
              <p className="mb-2 text-[13px] text-ink-3">{t("followUps")}</p>
              <div className="flex flex-wrap gap-2">
                {followUps.map((q) => (
                  <Button key={q} variant="chip" className="h-auto whitespace-normal py-2 text-left" onClick={() => void ask(q, q, facts)}>
                    {q}
                  </Button>
                ))}
              </div>
            </div>
          )}
          <div ref={bottom} />
        </div>

        {consent === "asking" && (
          <section className="mb-2 rounded-2xl border border-line bg-marigold-050 p-3" aria-labelledby="consent-title">
            <h2 id="consent-title" className="text-[15px] font-bold">{tp("title")}</h2>
            <p className="text-[14px] text-ink-2">{tp("body")}</p>
            <div className="mt-2 flex gap-2">
              <Button variant="accent" onClick={() => void answerConsent(true)}>{tp("yes")}</Button>
              <Button variant="secondary" onClick={() => void answerConsent(false)}>{tp("no")}</Button>
            </div>
          </section>
        )}
        {info && <p className="mb-2 text-center text-[13px] text-ok-700" role="status">{info}</p>}
        {consent === "yes" && (
          <button type="button" onClick={() => void removeMyData()} className="mx-auto mb-2 block min-h-11 text-[13px] font-semibold text-ink-3 underline">
            {tp("delete")}
          </button>
        )}

        <Composer value={input} onChange={setInput} onSend={submit} onStop={() => void stop()} busy={busy} />
      </div>
      <CasePanel facts={facts} saved={consent === "yes"} />
    </div>
  );
}

"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { AddService, SourceList } from "@/components/case/add-service";
import { dateWhen } from "@/components/case/case-tile";
import { AlertIcon, CheckIcon, LinkIcon, XIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import {
  addNote,
  addTodo,
  deleteCase,
  deleteNote,
  deleteTodo,
  downloadSummary,
  patchCase,
  recordStep,
  tickCustomDocument,
  tickTodo,
  undoStep,
  type CaseCard,
  type Check,
  type KeyDateKind,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const input = "min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px] md:w-72";
const heading = "text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700";
const panel = "rounded-2xl border border-line bg-surface p-4";
const linkCls = "inline-flex min-h-11 items-center gap-2 text-[15px] font-semibold text-teal-700 underline decoration-teal-700/30 underline-offset-4 hover:decoration-teal-700";

type Tr = (key: string, values?: Record<string, string | number>) => string;
const today = () => new Date().toISOString().slice(0, 10);

export function CaseDetail({ card, onChange, onClose }: { card: CaseCard; onChange: () => Promise<void>; onClose: () => void }) {
  const t = useTranslations("case");
  const tt = t as unknown as Tr;
  const td = useTranslations("docs") as unknown as Tr;
  const locale = useLocale();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState(card.submission?.submitted_on ?? "");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [days, setDays] = useState(card.overview.follow_up.user_set ? String(card.overview.follow_up.days) : "");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);
  const [todo, setTodo] = useState("");
  const [kdOn, setKdOn] = useState(card.key_date?.on ?? "");
  const [kdKind, setKdKind] = useState<KeyDateKind>(card.key_date?.kind ?? "deadline");
  const [kdLabel, setKdLabel] = useState(card.key_date?.label ?? "");

  const j = card.journey;
  const ov = card.overview;
  const fu = ov.follow_up;
  const links = card.links;
  const name = card.service_name ?? card.service_id;
  const custom = card.custom;

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    const ok = await fn();
    if (ok === false || ok === null) setError(t("saveError"));
    else await onChange();
    setBusy(false);
  }

  async function mark(step: number) {
    if (step === 4 && date && date > today()) return setError(t("futureDate"));
    if (step === 5 && reference.replace(/[^A-Za-z0-9]/g, "").length < 4) return setError(t("tooShort"));
    const extra: { submitted_on?: string; reference?: string } = {};
    if (step === 4 && date) extra.submitted_on = date;
    if (step === 5) extra.reference = reference;
    await run(async () => {
      const r = await recordStep(card.id, step, extra);
      if ("error" in r) return false;
      setReference("");
      return true;
    });
  }

  async function onSummary() {
    const blob = await downloadSummary(card.id, locale);
    if (!blob) return setError(t("saveError"));
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sahaay-case-summary.pdf";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (editing && custom) {
    return (
      <AddService
        existing={card}
        onCancel={() => setEditing(false)}
        onSaved={async () => {
          setEditing(false);
          await onChange();
        }}
      />
    );
  }

  const eligibilityQ = `/chat?q=${encodeURIComponent(tt("eligQuestion", { name }))}`;
  const portalCta = links.official_url
    ? { href: links.official_url, label: t("openPortal"), external: true }
    : custom?.portal_url
      ? { href: custom.portal_url, label: t("yourLink"), external: true }
      : null;
  const cta: { href: string; label: string; external?: boolean } | null = {
    check_eligibility: { href: eligibilityQ, label: t("ctaEligibility") },
    add_documents: custom ? { href: "#check-h", label: t("yourDocs") } : { href: "/documents", label: t("openDocs") },
    fill_form: { href: links.forms.length ? "/forms" : "/chat", label: links.forms.length ? t("openForm") : t("openChat") },
    submit: portalCta,
    follow_up: { href: "/drafts?kind=rti", label: t("ctaRti") },
    confirm_documents: null,
    save_reference: null,
    wait: null,
    done: null,
  }[ov.next_action];

  return (
    <div className="space-y-5">
      <header>
        {custom && (
          <span className="mb-2 inline-block rounded-full bg-bg-sunken px-2.5 py-0.5 text-[12px] font-semibold text-ink-2">{t("addedByYou")}</span>
        )}
        <h2 className="font-display text-[26px] font-extrabold leading-tight">{name}</h2>
        {card.department && <p className="text-[14.5px] text-ink-3">{card.department}</p>}
        {custom && (
          <div className="mt-3 rounded-xl bg-bg-sunken p-3 text-[14px] text-ink-2" role="note" data-testid="custom-note">
            <p>{t("customNote")}</p>
            {custom.ai_suggested && <p className="mt-1 font-semibold text-warn-700">{t("customAiNote")}</p>}
            <Button variant="secondary" className="mt-3" onClick={() => setEditing(true)} data-testid="edit-service">
              {t("editService")}
            </Button>
          </div>
        )}
        {card.prerequisites.length > 0 && (
          <p className="mt-2 text-[14.5px] text-ink-2">{tt("prereq", { names: card.prerequisites.map((p) => p.name).join(", ") })}</p>
        )}
      </header>

      {/* The single next action */}
      <section aria-labelledby="next-h" className="rounded-2xl border border-teal-700 bg-teal-100 p-4">
        <h3 id="next-h" className={heading}>
          {t("nextAction")}
        </h3>
        <p className="mt-1 text-[17px] font-bold" data-testid="next-action">
          {tt(`na.${ov.next_action}`)}
        </p>
        <p className="mt-1 text-[14.5px] text-ink-2">{tt(`nd.${ov.next_action}`)}</p>
        {cta && (
          <div className="mt-3">
            <Button asChild>
              {cta.external ? (
                <a href={cta.href} target="_blank" rel="noopener noreferrer">
                  {cta.label}
                  <LinkIcon />
                </a>
              ) : (
                <Link href={cta.href}>{cta.label}</Link>
              )}
            </Button>
          </div>
        )}
      </section>

      {fu.due && (
        <section role="status" className="rounded-2xl bg-warn-100 p-4 text-warn-700" data-testid="follow-up-due">
          <p className="flex items-start gap-2 font-semibold">
            <AlertIcon className="mt-0.5 size-5 shrink-0" />
            {tt("dueTitle", { days: fu.days ?? 0 })}
          </p>
          <p className="mt-1 text-[14.5px]">{t("dueBody")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button asChild variant="secondary"><Link href="/drafts?kind=rti">{t("ctaRti")}</Link></Button>
            <Button asChild variant="secondary"><Link href="/drafts?kind=cpgrams">{t("ctaCpgrams")}</Link></Button>
            <Button asChild variant="secondary"><Link href={`/drafts?kind=${links.draft_kind}`}>{t("ctaComplaint")}</Link></Button>
          </div>
        </section>
      )}

      {/* Your own progress */}
      <section aria-labelledby="tracker-h" className={panel}>
        <h3 id="tracker-h" className="text-[17px] font-bold">
          {t("own")}
        </h3>
        <ol className="mt-4 space-y-3">
          {j.steps.map((s) => {
            const isCurrent = j.current === s.n;
            return (
              <li key={s.n} className="flex flex-wrap items-center gap-3" aria-current={isCurrent ? "step" : undefined}>
                <span
                  aria-hidden
                  className={cn(
                    "flex size-9 shrink-0 items-center justify-center rounded-full border-2 text-[14px] font-bold",
                    s.done && "border-teal-700 bg-teal-700 text-white",
                    isCurrent && "border-marigold-500 bg-marigold-500 text-ink",
                    !s.done && !isCurrent && "border-line text-ink-3",
                  )}
                >
                  {s.done ? <CheckIcon className="size-5" /> : s.n}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[15px] font-semibold">{tt(`s${s.n}`)}</p>
                  <p className="text-[13px] text-ink-3">
                    {s.done ? `${t("done")}${s.done_at ? ` · ${s.done_at.slice(0, 10)}` : ""}` : isCurrent ? t("current") : t("upcoming")}
                  </p>
                </div>
                {s.done ? (
                  <Button variant="ghost" disabled={busy} onClick={() => run(async () => (await undoStep(card.id, s.n)) !== null)} aria-label={`${t("undo")}: ${tt(`s${s.n}`)}`}>
                    {t("undo")}
                  </Button>
                ) : (
                  isCurrent &&
                  s.n !== 4 &&
                  s.n !== 5 && (
                    <Button variant="secondary" disabled={busy} onClick={() => mark(s.n)} aria-label={`${t("mark")}: ${tt(`s${s.n}`)}`}>
                      {t("mark")}
                    </Button>
                  )
                )}
              </li>
            );
          })}
        </ol>

        {(j.current === 4 || j.current === 5) && (
          <div className="mt-4 space-y-3 rounded-xl bg-bg-sunken p-4">
            {j.current === 4 && (
              <div>
                <label htmlFor="sub-date" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("submittedOn")}</label>
                <input id="sub-date" type="date" className={input} value={date} max={today()} onChange={(e) => setDate(e.target.value)} />
              </div>
            )}
            {j.current === 5 && (
              <div>
                <label htmlFor="sub-ref" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("reference")}</label>
                <input id="sub-ref" autoComplete="off" className={input} value={reference} onChange={(e) => setReference(e.target.value)} />
                <p className="mt-1 text-[13px] text-ink-3">{t("referenceHint")}</p>
              </div>
            )}
            <Button disabled={busy} onClick={() => mark(j.current!)} aria-label={`${t("mark")}: ${tt(`s${j.current}`)}`}>
              {t("mark")}
            </Button>
          </div>
        )}
        {card.submission?.submitted_on && <p className="mt-3 text-[14px] text-ink-2">{tt("submittedDate", { date: card.submission.submitted_on })}</p>}
        {card.submission?.reference_no_masked && <p className="text-[14px] text-ink-2">{tt("referenceKept", { ref: card.submission.reference_no_masked })}</p>}
        {error && (
          <p role="alert" className="mt-3 flex items-start gap-2 text-bad-700">
            <AlertIcon className="mt-0.5 size-5 shrink-0" />
            {error}
          </p>
        )}
      </section>

      {/* Smart checklist */}
      <section aria-labelledby="check-h" className={panel}>
        <h3 id="check-h" className="text-[17px] font-bold">{custom ? t("yourDocs") : t("readiness")}</h3>
        {(!custom || custom.documents.length > 0) && (
          <p className="mt-1 text-[15px]" data-testid="case-ready">
            {tt("readyCount", { done: ov.docs_ready, total: ov.docs_total })}
          </p>
        )}
        {custom ? (
          custom.documents.length === 0 ? (
            <p className="mt-2 text-[14.5px] text-ink-2">{t("noDocs")}</p>
          ) : (
            <ul className="mt-3 divide-y divide-line" data-testid="case-checklist">
              {custom.documents.map((d) => (
                <li key={d.id}>
                  <label className="flex min-h-11 cursor-pointer items-center justify-between gap-3 py-1 text-[15px]">
                    <span className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        className="size-5 shrink-0 accent-teal-700"
                        checked={d.have}
                        disabled={busy}
                        onChange={(e) => run(() => tickCustomDocument(card.id, locale, d.id, e.target.checked))}
                      />
                      {d.name}
                    </span>
                    <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-[12.5px] font-semibold", d.have ? "bg-ok-100 text-ok-700" : "bg-bad-100 text-bad-700")}>
                      {d.have ? t("docDeclared") : t("doc_missing")}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )
        ) : (
          <ul className="mt-3 divide-y divide-line" data-testid="case-checklist">
            {card.readiness.checks.map((c) => (
              <CheckRow key={c.doc_type} check={c} label={td(`types.${c.doc_type}`)} />
            ))}
          </ul>
        )}
        <p className="mt-2 text-[13.5px] text-ink-3">{t("readyCaption")}</p>
        {!custom && (
          <Button asChild variant="secondary" className="mt-3">
            <Link href="/documents">{t("openDocs")}</Link>
          </Button>
        )}
      </section>

      {/* Important date: the user's own reminder */}
      <section aria-labelledby="date-h" className={panel}>
        <h3 id="date-h" className="text-[17px] font-bold">{t("dateTitle")}</h3>
        <p className="mt-1 text-[14.5px] text-ink-2">{t("dateHelp")}</p>
        {card.key_date && (
          <p
            className={cn(
              "mt-3 inline-flex rounded-full px-3 py-1 text-[14px] font-semibold",
              card.key_date.passed ? "bg-bg-sunken text-ink-2" : card.key_date.soon ? "bg-marigold-500 text-ink" : "bg-teal-100 text-teal-700",
            )}
            data-testid="key-date"
          >
            {tt(`kind.${card.key_date.kind}`)}
            {card.key_date.label ? ` (${card.key_date.label})` : ""}: {card.key_date.on} · {dateWhen(tt, card.key_date)}
          </p>
        )}
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="kd-kind" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("dateKind")}</label>
            <select id="kd-kind" className={cn(input, "md:w-44")} value={kdKind} onChange={(e) => setKdKind(e.target.value as KeyDateKind)}>
              {(["deadline", "appointment", "other"] as const).map((k) => (
                <option key={k} value={k}>{tt(`kind.${k}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="kd-on" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("dateOn")}</label>
            <input id="kd-on" type="date" className={cn(input, "md:w-44")} value={kdOn} onChange={(e) => setKdOn(e.target.value)} />
          </div>
          <div className="min-w-0 flex-1 basis-48">
            <label htmlFor="kd-label" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("dateLabel")}</label>
            <input id="kd-label" maxLength={60} className={cn(input, "md:w-full")} value={kdLabel} onChange={(e) => setKdLabel(e.target.value)} />
          </div>
          <Button
            variant="secondary"
            disabled={busy || !kdOn}
            onClick={() => run(() => patchCase(card.id, locale, { key_date: kdOn, key_date_kind: kdKind, key_date_label: kdLabel.trim() }))}
            data-testid="save-date"
            aria-label={`${t("save")}: ${t("dateTitle")}`}
          >
            {t("save")}
          </Button>
          {card.key_date && (
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => run(async () => { setKdOn(""); setKdLabel(""); return patchCase(card.id, locale, { clear_key_date: true }); })}
            >
              {t("clearDate")}
            </Button>
          )}
        </div>
      </section>

      {/* To-do list */}
      <section aria-labelledby="todo-h" className={panel}>
        <h3 id="todo-h" className="text-[17px] font-bold">{t("todoTitle")}</h3>
        <p className="mt-1 text-[13.5px] text-ink-3">{t("todoHelp")}</p>
        {card.todos.length > 0 && (
          <>
            <p className="mt-2 text-[14px] text-ink-2">{tt("todoCount", { done: card.todos_done, total: card.todos.length })}</p>
            <ul className="mt-2 space-y-1" data-testid="case-todos">
              {card.todos.map((td_) => (
                <li key={td_.id} className="flex items-center justify-between gap-2 rounded-xl bg-bg-sunken pl-3">
                  <label className="flex min-h-11 flex-1 cursor-pointer items-center gap-3 text-[15px]">
                    <input
                      type="checkbox"
                      className="size-5 shrink-0 accent-teal-700"
                      checked={td_.done}
                      disabled={busy}
                      onChange={(e) => run(() => tickTodo(card.id, locale, td_.id, e.target.checked))}
                    />
                    <span className={cn(td_.done && "text-ink-3 line-through")}>{td_.text}</span>
                  </label>
                  <button type="button" onClick={() => run(() => deleteTodo(card.id, locale, td_.id))} aria-label={`${t("deleteTodo")}: ${td_.text}`} className="grid size-11 shrink-0 place-items-center rounded-full text-ink-2 hover:bg-line">
                    <XIcon className="size-5" />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
        <form
          className="mt-3 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!todo.trim()) return;
            void run(async () => { const r = await addTodo(card.id, locale, todo.trim()); if (r) setTodo(""); return r; });
          }}
        >
          <div className="min-w-0 flex-1 basis-56">
            <label htmlFor="todo" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("todoLabel")}</label>
            <input id="todo" maxLength={120} className={cn(input, "md:w-full")} value={todo} onChange={(e) => setTodo(e.target.value)} />
          </div>
          <Button type="submit" variant="secondary" disabled={busy || !todo.trim()}>{t("addTodo")}</Button>
        </form>
      </section>

      {/* Steps for this service, from the scheme data */}
      {card.steps_text.length > 0 && (
        <section aria-labelledby="how-h" className={panel}>
          <h3 id="how-h" className="text-[17px] font-bold">{custom ? t("yourSteps") : t("howTitle")}</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-[15px] text-ink-2">
            {card.steps_text.map((s) => (
              <li key={s.n}>{s.text}</li>
            ))}
          </ol>
        </section>
      )}

      {/* Links */}
      <section aria-labelledby="links-h" className={panel}>
        <h3 id="links-h" className="text-[17px] font-bold">{t("linksTitle")}</h3>
        <ul className="mt-2 space-y-0.5" data-testid="case-links">
          <li>
            <Link className={linkCls} href={eligibilityQ}>{t("ctaEligibility")}</Link>
            <p className="text-[13px] text-ink-3">{t("eligNote")}</p>
          </li>
          {links.official_url && (
            <li>
              <a className={linkCls} href={links.official_url} target="_blank" rel="noopener noreferrer">
                <LinkIcon className="size-5" />
                {t("openPortal")}
              </a>
            </li>
          )}
          {custom?.portal_url && !custom.portal_official && (
            <li>
              <a className={linkCls} href={custom.portal_url} target="_blank" rel="noopener noreferrer">
                <LinkIcon className="size-5" />
                {t("yourLink")}
              </a>
              <p className="text-[13px] text-ink-3">{t("notCheckedBadge")}</p>
            </li>
          )}
          {links.forms.map((f) => (
            <li key={f.id}>
              <Link className={linkCls} href="/forms">{t("openForm")}</Link>
              <p className="text-[13px] text-ink-3">
                <a className="underline" href={f.source_url} target="_blank" rel="noopener noreferrer">{f.title}</a> · {tt("checkedOn", { date: f.date_checked })}
              </p>
            </li>
          ))}
          <li><Link className={linkCls} href={`/drafts?kind=${links.draft_kind}`}>{t("ctaComplaint")}</Link></li>
          <li><Link className={linkCls} href="/drafts?kind=rti">{t("ctaRti")}</Link></li>
          <li><Link className={linkCls} href="/drafts?kind=cpgrams">{t("ctaCpgrams")}</Link></li>
        </ul>
        {custom && custom.sources.length > 0 && (
          <div className="mt-3 text-[14px]">
            <SourceList sources={custom.sources} heading={tt("aiSources", { date: custom.added_on ?? "" })} />
          </div>
        )}
        {links.sources.length > 0 && (
          <>
            <h4 className={cn(heading, "mt-4")}>{t("sourcesTitle")}</h4>
            <ul className="mt-1 space-y-1 text-[14px]">
              {links.sources.map((s) => (
                <li key={s.url}>
                  <a className="break-words text-teal-700 underline" href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>
                  <span className="text-ink-3"> · {s.publisher}{s.date_checked ? ` · ${tt("checkedOn", { date: s.date_checked })}` : ""}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* Follow-up reminder */}
      <section aria-labelledby="fu-h" className={panel}>
        <h3 id="fu-h" className="text-[17px] font-bold">{t("followTitle")}</h3>
        <p className="mt-1 text-[14.5px] text-ink-2">{t("followHelp")}</p>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="fu-days" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("followDays")}</label>
            <input id="fu-days" inputMode="numeric" className={cn(input, "md:w-40")} value={days} onChange={(e) => setDays(e.target.value.replace(/\D/g, "").slice(0, 3))} placeholder={fu.days && !fu.user_set ? String(fu.days) : ""} />
          </div>
          <Button
            variant="secondary"
            disabled={busy || !days || Number(days) < 1}
            onClick={() => run(() => patchCase(card.id, locale, { follow_up_days: Number(days) }))}
          >
            {t("save")}
          </Button>
          {fu.user_set && (
            <Button variant="ghost" disabled={busy} onClick={() => run(async () => { setDays(""); return patchCase(card.id, locale, { clear_follow_up: true }); })}>
              {custom ? t("useEstimate") : t("useDefault")}
            </Button>
          )}
        </div>
        <p className="mt-2 text-[14px] text-ink-2">
          {fu.due_on ? tt("followOn", { date: fu.due_on }) : fu.days === null ? (custom ? t("customNoTimeline") : t("followUnknown")) : t("followAfterSubmit")}
          {!fu.user_set && fu.days !== null ? ` ${tt(custom ? "customTimeline" : "followDefault", { days: fu.days })}` : ""}
        </p>
        {card.submission?.submitted_on && (
          <label className="mt-3 flex min-h-11 cursor-pointer items-center gap-3 text-[15px]">
            <input
              type="checkbox"
              className="size-5 accent-teal-700"
              checked={fu.reply_received}
              disabled={busy}
              onChange={(e) => run(() => patchCase(card.id, locale, { reply_received: e.target.checked }))}
            />
            {t("replyReceived")}
          </label>
        )}
      </section>

      {/* Notes and timeline */}
      <section aria-labelledby="notes-h" className={panel}>
        <h3 id="notes-h" className="text-[17px] font-bold">{t("notesTitle")}</h3>
        <p className="mt-1 text-[13.5px] text-ink-3">{t("notesHelp")}</p>
        <div className="mt-3 flex flex-wrap items-start gap-3">
          <div className="min-w-0 flex-1">
            <label htmlFor="note" className="mb-1 block text-[14px] font-semibold text-ink-2">{t("noteLabel")}</label>
            <textarea id="note" maxLength={300} rows={2} className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-[15px]" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <Button
            className="mt-7"
            variant="secondary"
            disabled={busy || !note.trim()}
            onClick={() => run(async () => { const r = await addNote(card.id, locale, note.trim()); if (r) setNote(""); return r; })}
          >
            {t("addNote")}
          </Button>
        </div>
        {card.notes.length > 0 && (
          <ul className="mt-3 space-y-2" data-testid="case-notes">
            {[...card.notes].reverse().map((n) => (
              <li key={n.id} className="flex items-start justify-between gap-3 rounded-xl bg-bg-sunken px-3 py-2 text-[14.5px]">
                <span>
                  <span className="block text-[12.5px] text-ink-3">{n.at.slice(0, 10)}</span>
                  {n.text}
                </span>
                <button type="button" onClick={() => run(() => deleteNote(card.id, locale, n.id))} aria-label={t("deleteNote")} className="grid size-11 shrink-0 place-items-center rounded-full text-ink-2 hover:bg-line">
                  <XIcon className="size-5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={onSummary}>{t("summary")}</Button>
        <Button asChild variant="secondary"><Link href="/chat">{t("openChat")}</Link></Button>
        {confirmDelete ? (
          <span className="flex flex-wrap items-center gap-2" role="group" aria-label={t("deleteTitle")}>
            <span className="text-[14.5px] font-semibold">{t("deleteAsk")}</span>
            <Button variant="secondary" onClick={async () => { if (await deleteCase(card.id)) { await onChange(); onClose(); } else setError(t("saveError")); }}>{t("deleteYes")}</Button>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>{t("deleteNo")}</Button>
          </span>
        ) : (
          <Button variant="ghost" onClick={() => setConfirmDelete(true)}>{t("deleteTitle")}</Button>
        )}
      </div>
    </div>
  );
}

function CheckRow({ check, label }: { check: Check; label: string }) {
  const t = useTranslations("case");
  const tt = t as unknown as Tr;
  const ok = check.status === "ok";
  const chip = ok ? "bg-ok-100 text-ok-700" : check.required ? "bg-bad-100 text-bad-700" : "bg-warn-100 text-warn-700";
  const text = ok
    ? check.evaluated === "scanned_and_confirmed"
      ? t("docChecked")
      : t("docDeclared")
    : tt(`doc_${check.status}`);
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <span className="flex items-center gap-2 text-[15px]">
        <span className={cn("inline-flex size-6 shrink-0 items-center justify-center rounded-full", chip)}>
          {ok ? <CheckIcon className="size-4" /> : <XIcon className="size-4" />}
        </span>
        <span>
          {label}
          {!check.required && <span className="text-ink-3"> · {t("optional")}</span>}
          {check.expires_on && <span className="block text-[12.5px] text-ink-3">{tt("validUntil", { date: check.expires_on })}</span>}
        </span>
      </span>
      <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-[12.5px] font-semibold", chip)}>{text}</span>
    </li>
  );
}

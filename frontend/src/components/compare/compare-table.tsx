"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AlertIcon, ShieldCheckIcon } from "@/components/icons";
import { API_URL } from "@/lib/sse";
import { cn } from "@/lib/utils";

interface ServiceLite {
  id: string;
  name: { en: string | null; hi: string | null; hn: string | null };
}
interface Row {
  id: string;
  name: string;
  department: string;
  status: "verified" | "partial";
  stale: boolean;
  benefit: string | null;
  eligibility: string[];
  exclusions: string[];
  prerequisites: string[];
  fee_strip: { official_fee_inr: number | null; csc_max_inr: number | null; processing_days: number | null; day_type: string | null };
  citations: { n: number; title: string; url: string; date_checked: string | null }[];
}

export function CompareTable() {
  const t = useTranslations("compare");
  const tc = useTranslations("card");
  const locale = useLocale() as "en" | "hi" | "hn";
  const format = useFormatter();
  const [all, setAll] = useState<ServiceLite[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    fetch(`${API_URL}/services`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((list: ServiceLite[]) => {
        setAll(list);
        setPicked(list.slice(0, 2).map((s) => s.id));
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    if (picked.length < 2) {
      setRows(null);
      return;
    }
    setState("loading");
    fetch(`${API_URL}/compare?ids=${picked.join(",")}&lang=${locale}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d: { services: Row[] }) => {
        setRows(d.services);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [picked, locale]);

  function toggle(id: string) {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < 3 ? [...p, id] : p));
  }

  const inr = (v: number | null) =>
    v === null ? tc("verifyLocally") : v === 0 ? t("free") : format.number(v, { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  const names = new Map(all.map((s) => [s.id, s.name[locale] ?? s.name.en ?? s.id]));

  const lines: { label: string; cell: (r: Row) => React.ReactNode }[] = rows
    ? [
        { label: t("department"), cell: (r) => r.department },
        { label: t("benefit"), cell: (r) => r.benefit ?? tc("verifyLocally") },
        { label: t("who"), cell: (r) => <List items={r.eligibility} empty={t("none")} /> },
        { label: t("exclusions"), cell: (r) => <List items={r.exclusions} empty={t("none")} /> },
        { label: t("first"), cell: (r) => <List items={r.prerequisites.map((p) => names.get(p) ?? p)} empty={t("none")} /> },
        { label: tc("officialFee"), cell: (r) => inr(r.fee_strip.official_fee_inr) },
        { label: tc("cscMax"), cell: (r) => inr(r.fee_strip.csc_max_inr) },
        {
          label: tc("processing"),
          cell: (r) =>
            r.fee_strip.processing_days === null
              ? tc("verifyLocally")
              : tc("days", { n: r.fee_strip.processing_days, type: r.fee_strip.day_type ?? "other" }),
        },
        {
          label: t("sources"),
          cell: (r) => (
            <ul className="space-y-1">
              {r.citations.map((c) => (
                <li key={c.n}>
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                    [{c.n}] {c.title}
                  </a>
                  <span className="block text-[12.5px] text-ink-3">
                    {c.date_checked ? tc("checkedOn", { date: c.date_checked }) : tc("notChecked")}
                  </span>
                </li>
              ))}
            </ul>
          ),
        },
      ]
    : [];

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="mb-2 text-[15px] font-semibold">{t("pick")}</legend>
        <div className="flex flex-wrap gap-2">
          {all.map((s) => {
            const on = picked.includes(s.id);
            return (
              <button
                key={s.id}
                type="button"
                aria-pressed={on}
                onClick={() => toggle(s.id)}
                className={cn(
                  "min-h-11 rounded-full border px-4 text-left text-[14px] font-semibold",
                  on ? "border-teal-700 bg-teal-700 text-white" : "border-teal-700 bg-surface text-teal-700",
                )}
              >
                {names.get(s.id)}
              </button>
            );
          })}
        </div>
      </fieldset>

      {state === "error" && <p role="alert" className="text-bad-700">{t("error")}</p>}
      {state === "loading" && picked.length >= 2 && <p role="status" className="text-ink-3">{t("loading")}</p>}

      {rows && state === "ready" && (
        <div className="overflow-x-auto rounded-[20px] border border-line bg-surface">
          <table className="w-full min-w-[34rem] border-collapse text-left text-[15px]">
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className="sr-only">{t("title")}</th>
                {rows.map((r) => {
                  const ok = r.status === "verified" && !r.stale;
                  return (
                    <th key={r.id} scope="col" className="p-3 align-top font-display text-[17px] font-bold">
                      {r.name}
                      <span
                        className={cn(
                          "mt-1 flex w-fit items-center gap-1.5 rounded-full px-2.5 py-0.5 font-sans text-[12.5px] font-semibold",
                          ok ? "bg-ok-100 text-ok-700" : "bg-warn-100 text-warn-700",
                        )}
                      >
                        {ok ? <ShieldCheckIcon className="size-4" /> : <AlertIcon className="size-4" />}
                        {ok ? tc("verifiedShort") : tc("verifyLocally")}
                      </span>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.label} className="border-b border-line last:border-0">
                  <th scope="row" className="w-32 p-3 align-top text-[13px] font-semibold uppercase tracking-[0.05em] text-ink-3">
                    {l.label}
                  </th>
                  {rows.map((r) => (
                    <td key={r.id} className="p-3 align-top">
                      {l.cell(r)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function List({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <span className="text-ink-3">{empty}</span>;
  return (
    <ul className="list-disc space-y-1 pl-4">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  );
}

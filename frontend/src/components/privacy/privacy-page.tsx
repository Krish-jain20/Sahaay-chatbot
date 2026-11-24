"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { deleteMyData, loadMyData, type MyData } from "@/lib/api";

export function MyDataPanel() {
  const t = useTranslations("privacy");
  const tf = useTranslations("facts");
  const tc = useTranslations("docs");
  const [data, setData] = useState<MyData | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [confirm, setConfirm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    loadMyData().then((d) => {
      setData(d);
      setState(d ? "ready" : "error");
    });
  }, []);
  useEffect(load, [load]);

  async function onDelete() {
    setFailed(false);
    if (await deleteMyData()) {
      setMessage(t("deleted"));
      setConfirm(false);
      load();
    } else setFailed(true);
  }

  const label = (k: string) => (tf as unknown as (key: string) => string)(k);
  const docName = (k: string) => (tc as unknown as (key: string) => string)(`types.${k}`);
  const empty = data && data.facts.length === 0 && data.cases.length === 0;

  return (
    <div className="space-y-6">
      <section aria-labelledby="mydata-h" className="rounded-2xl border border-line bg-surface p-4">
        <h2 id="mydata-h" className="text-[17px] font-bold">{t("yourData")}</h2>
        {state === "loading" && <p className="mt-2 text-ink-2">{t("loading")}</p>}
        {state === "error" && <p role="alert" className="mt-2 text-bad-700">{t("error")}</p>}
        {empty && <p className="mt-2 text-ink-2" data-testid="no-data">{t("none")}</p>}
        {data && data.facts.length > 0 && (
          <div className="mt-3">
            <h3 className="text-[14px] font-semibold text-ink-2">{t("facts")}</h3>
            <ul className="mt-1 space-y-1 text-[15px]">
              {data.facts.map((f) => (
                <li key={f.key}>{label(f.key)}: {String(f.value)}</li>
              ))}
            </ul>
          </div>
        )}
        {data?.cases.map((c) => (
          <div key={c.id} className="mt-3">
            <h3 className="text-[14px] font-semibold text-ink-2">{t("cases")}: {c.service_id}</h3>
            <ul className="mt-1 space-y-1 text-[15px]">
              {c.documents.length > 0 && <li>{t("docs")}: {c.documents.map((d) => docName(d.doc_type)).join(", ")}</li>}
              {c.steps.length > 0 && <li>{t("steps")}: {c.steps.map((s) => s.step).sort().join(", ")}</li>}
              {c.submission?.submitted_on && <li>{t("submission")}: {c.submission.submitted_on}</li>}
              {c.submission?.reference_no_masked && <li>{c.submission.reference_no_masked}</li>}
            </ul>
          </div>
        ))}
        {message && <p role="status" className="mt-3 font-semibold text-teal-700">{message}</p>}
      </section>

      <section aria-labelledby="del-h" className="space-y-3 rounded-2xl border border-line bg-surface p-4">
        <h2 id="del-h" className="text-[17px] font-bold">{t("deleteTitle")}</h2>
        <p className="text-[15px] text-ink-2">{t("deleteHelp")}</p>
        <label className="flex min-h-11 items-center gap-3 text-[15px]">
          <input type="checkbox" className="size-5" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
          {t("deleteConfirm")}
        </label>
        <Button variant="secondary" disabled={!confirm} onClick={onDelete}>{t("deleteButton")}</Button>
        {failed && <p role="alert" className="text-bad-700">{t("deleteError")}</p>}
      </section>
    </div>
  );
}

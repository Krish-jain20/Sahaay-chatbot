"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { accountState, sendSignInLink, signOut, type AccountState } from "@/lib/supabase";

export function AccountPanel() {
  const t = useTranslations("account");
  const [acct, setAcct] = useState<AccountState | null>(null);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sent" | "error">("idle");

  useEffect(() => {
    accountState().then(setAcct);
  }, []);

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    setStatus((await sendSignInLink(email.trim())) ? "sent" : "error");
  }
  async function onSignOut() {
    await signOut();
    setAcct(await accountState());
  }

  if (!acct) return null;
  return (
    <section aria-labelledby="acct-h" className="space-y-3 rounded-2xl border border-line bg-surface p-4">
      <h2 id="acct-h" className="text-[17px] font-bold">{t("title")}</h2>
      {!acct.configured && <p className="text-[15px] text-ink-2" data-testid="signin-unavailable">{t("unavailable")}</p>}
      {acct.configured && !acct.guest && (
        <>
          <p className="text-[15px] text-ink-2">{t("signedIn", { email: acct.email ?? "" })}</p>
          <Button variant="secondary" onClick={onSignOut}>{t("signOut")}</Button>
        </>
      )}
      {acct.configured && acct.guest && (
        <form onSubmit={onSend} className="space-y-3">
          <p className="text-[15px] text-ink-2">{t("guestHelp")}</p>
          <label className="block text-[14px] font-semibold text-ink-2" htmlFor="acct-email">{t("emailLabel")}</label>
          <input
            id="acct-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="min-h-11 w-full rounded-xl border border-line bg-bg px-3 text-[16px]"
          />
          <Button type="submit">{t("send")}</Button>
          {status === "sent" && <p role="status" className="font-semibold text-teal-700">{t("sent")}</p>}
          {status === "error" && <p role="alert" className="text-bad-700">{t("error")}</p>}
        </form>
      )}
    </section>
  );
}

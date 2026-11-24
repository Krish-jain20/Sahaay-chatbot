import { useTranslations } from "next-intl";

import { CheckIcon, HelpIcon } from "@/components/icons";

/** A still picture of the product, not a working chat: everything here is decorative and hidden from assistive tech. */
export function ChatPreview() {
  const t = useTranslations("home.preview");
  const rise = (ms: number) => ({ animationDelay: `${ms}ms` });
  return (
    <figure className="relative mx-auto w-full max-w-[30rem] lg:mx-0 lg:ml-auto">
      <div className="absolute -right-3 -top-3 hidden size-24 rounded-3xl bg-marigold-100 sm:block" aria-hidden="true" />
      <div className="relative rounded-[28px] border border-line bg-teal-100 p-3 sm:p-4" aria-hidden="true">
        <div className="space-y-3 rounded-[20px] bg-bg p-4">
          <div className="animate-rise ml-auto w-fit max-w-[85%] rounded-[20px_20px_6px_20px] bg-teal-700 px-4 py-2.5 text-[14.5px] text-white" style={rise(0)}>
            {t("user")}
          </div>
          <div className="animate-rise flex flex-wrap gap-2" style={rise(250)}>
            {(["step1", "step2"] as const).map((k) => (
              <span key={k} className="inline-flex items-center gap-1.5 rounded-full bg-bg-sunken px-3 py-1 text-[12.5px] text-ink-2">
                <CheckIcon className="size-3.5 text-ok-700" />
                {t(k)}
              </span>
            ))}
          </div>
          <div className="animate-rise w-[92%] space-y-3 rounded-[20px_20px_20px_6px] border border-line bg-surface p-4" style={rise(500)}>
            <p className="font-display text-[17px] font-bold leading-snug text-ink">{t("title")}</p>
            <ul className="space-y-2 text-[14px]">
              <li className="flex items-center gap-2.5">
                <span className="grid size-6 place-items-center rounded-full bg-ok-100 text-ok-700">
                  <CheckIcon className="size-4" />
                </span>
                {t("met")}
              </li>
              <li className="flex items-center gap-2.5">
                <span className="grid size-6 place-items-center rounded-full bg-warn-100 text-warn-700">
                  <HelpIcon className="size-4" />
                </span>
                {t("unknown")}
              </li>
            </ul>
            <p className="rounded-xl bg-teal-100 px-3 py-2 text-[12.5px] text-ink-2">{t("source")}</p>
          </div>
          <div className="animate-rise flex gap-2" style={rise(750)}>
            <span className="rounded-full border border-teal-700 px-3.5 py-1.5 text-[13.5px] text-teal-700">{t("chip")}</span>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-[12.5px] text-ink-3 lg:text-right">{t("caption")}</figcaption>
    </figure>
  );
}

import Link from "next/link";
import { useTranslations } from "next-intl";

import {
  ArrowRightIcon,
  ChatIcon,
  ClipboardIcon,
  FileIcon,
  FolderIcon,
  LifebuoyIcon,
  PenIcon,
  ScaleIcon,
} from "@/components/icons";
import { cn } from "@/lib/utils";

const TOOLS = [
  { id: "chat", href: "/chat", Icon: ChatIcon, wide: true },
  { id: "compare", href: "/compare", Icon: ScaleIcon },
  { id: "documents", href: "/documents", Icon: FileIcon },
  { id: "drafts", href: "/drafts", Icon: PenIcon },
  { id: "forms", href: "/forms", Icon: ClipboardIcon },
  { id: "help", href: "/help", Icon: LifebuoyIcon },
  { id: "case", href: "/case", Icon: FolderIcon },
] as const;

export function ToolsGrid() {
  const t = useTranslations("home.tools");
  const tn = useTranslations("nav");
  return (
    <section aria-labelledby="tools-h" className="border-t border-line py-14 lg:py-20">
      <div className="max-w-xl">
        <p className="text-[11px] font-semibold uppercase tracking-[0.05em] text-teal-700">{t("eyebrow")}</p>
        <h2 id="tools-h" className="mt-3 text-[30px] font-extrabold leading-[1.08] sm:text-[36px]">{t("title")}</h2>
        <p className="mt-3 text-[16.5px] text-ink-2">{t("sub")}</p>
      </div>
      <ul className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TOOLS.map(({ id, href, Icon, ...rest }) => {
          const wide = "wide" in rest;
          return (
            <li key={id} className={cn(wide && "lg:col-span-2")}>
              <Link
                href={href}
                data-testid={`tool-${id}`}
                className={cn(
                  "group flex h-full min-h-44 flex-col rounded-[20px] border p-5 transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_24px_rgba(15,76,92,0.12)] motion-reduce:transition-none motion-reduce:hover:translate-y-0",
                  wide ? "border-teal-700 bg-teal-700 text-white" : "border-line bg-surface text-ink",
                )}
              >
                <span className={cn("grid size-11 place-items-center rounded-xl", wide ? "bg-white/15 text-white" : "bg-teal-100 text-teal-700")}>
                  <Icon className="size-6" />
                </span>
                <span className="mt-5 block font-display text-[21px] font-bold leading-tight">
                  {id === "compare" ? t("compareName") : tn(id)}
                </span>
                <span className={cn("mt-1.5 block text-[15px]", wide ? "text-white/85" : "text-ink-2")}>{t(`${id}Desc`)}</span>
                <span className={cn("mt-auto inline-flex items-center gap-1.5 pt-4 text-[14px] font-semibold", wide ? "text-white" : "text-teal-700")}>
                  {t("open")}
                  <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" />
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

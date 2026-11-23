"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

export function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const path = usePathname();
  const active = href === "/" ? path === "/" : path.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-11 items-center rounded-full px-4 text-[15px] font-semibold",
        active ? "bg-teal-700 text-white" : "text-ink-2 hover:bg-bg-panel",
      )}
    >
      {children}
    </Link>
  );
}

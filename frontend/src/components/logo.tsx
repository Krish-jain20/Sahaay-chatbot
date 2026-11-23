import Link from "next/link";

/** Open arch (bridge / cupped hand) with a marigold dot. No emblem, flag or department logo. */
export function Logo() {
  return (
    <Link href="/" className="inline-flex min-h-11 items-center gap-2 rounded-full pr-2" aria-label="Sahaay home">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <path d="M5 22V16a11 11 0 0 1 22 0v6" fill="none" stroke="var(--teal-700)" strokeWidth="4" strokeLinecap="round" />
        <circle cx="16" cy="26" r="3" fill="var(--marigold-500)" />
      </svg>
      <span className="font-display text-xl font-extrabold text-teal-700">Sahaay</span>
    </Link>
  );
}

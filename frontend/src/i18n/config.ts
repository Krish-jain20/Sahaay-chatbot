export const locales = ["en", "hi", "hn"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const LOCALE_COOKIE = "sahaay_locale";

export function isLocale(v: string | undefined): v is Locale {
  return !!v && (locales as readonly string[]).includes(v);
}

/** BCP 47 tag for the html lang attribute. Hinglish is Hindi in Latin script. */
export const htmlLang: Record<Locale, string> = { en: "en", hi: "hi", hn: "hi-Latn" };

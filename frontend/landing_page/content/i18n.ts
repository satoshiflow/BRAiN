export type Lang = "de" | "en";

export const LANGS: Lang[] = ["de", "en"];

export function getInitialLang(searchParams?: Record<string, string | string[] | undefined>): Lang {
  const q = searchParams?.lang;
  const v = Array.isArray(q) ? q[0] : q;
  return v === "en" ? "en" : "de";
}

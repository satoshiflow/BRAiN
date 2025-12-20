"use client";

import React from "react";
import type { Lang } from "@/content/i18n";

export function LanguageToggle({
  lang,
  onChange,
}: {
  lang: Lang;
  onChange: (l: Lang) => void;
}) {
  return (
    <div className="inline-flex rounded-xl border border-white/15 bg-white/5 p-1">
      <button
        className={`px-3 py-1.5 rounded-lg text-sm ${lang === "de" ? "bg-white text-black" : "text-white/80"}`}
        onClick={() => onChange("de")}
        type="button"
      >
        DE
      </button>
      <button
        className={`px-3 py-1.5 rounded-lg text-sm ${lang === "en" ? "bg-white text-black" : "text-white/80"}`}
        onClick={() => onChange("en")}
        type="button"
      >
        EN
      </button>
    </div>
  );
}

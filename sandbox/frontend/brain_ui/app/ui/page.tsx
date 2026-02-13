"use client";

import { useRouter } from "next/navigation";
import { MouseEvent } from "react";
import { cn } from "@/lib/utils";
import { usePresenceStore } from "@/brain-ui/state/presenceStore";

type Mode = "circle" | "avatar";

const MODES = [
  {
    id: "circle" as Mode,
    label: "Presence Circle",
    tagline: "Minimal, ambient, always there.",
    description:
      "Ein reduzierter, pulsierender Kreis – perfekt, wenn du Fokus auf den Inhalt möchtest und Präsenz eher subtil wahrnehmen willst."
  },
  {
    id: "avatar" as Mode,
    label: "Full Avatar",
    tagline: "Expressive, emotional, more human.",
    description:
      "Ein ausdrucksstarker Avatar mit Emotionen und Mikroanimationen – ideal, wenn du eine visuellere Interaktion mit BRAiN möchtest."
  }
];

export default function UiOnboardingPage() {
  const router = useRouter();
  const setMode = usePresenceStore((state) => state.setMode);

  const handleSelect = (mode: Mode) => (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setMode(mode);
    router.push("/ui/chat");
  };

  return (
    <div className="flex flex-col gap-8 md:gap-10">
      <div className="max-w-2xl">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-white/60 mb-4">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-sky-400" />
          <span>Step 1 · Choose my presence</span>
        </div>
        <h1 className="text-2xl md:text-3xl lg:text-4xl font-semibold tracking-tight text-white mb-3">
          How would you like to meet me?
        </h1>
        <p className="text-sm md:text-base text-white/60">
          Wähle, wie BRAiN sich in der UI zeigt: als dezenter{" "}
          <span className="text-white/80">Presence Circle</span> oder als{" "}
          <span className="text-white/80">voller Avatar</span> mit Emotionen.
          Du kannst das später jederzeit in den Einstellungen ändern.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
        {MODES.map((mode) => (
          <button
            key={mode.id}
            type="button"
            onClick={handleSelect(mode.id)}
            className={cn(
              "group relative w-full overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-5 md:p-6 text-left transition",
              "hover:border-sky-400/70 hover:bg-white/10 hover:shadow-[0_0_40px_rgba(56,189,248,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/80"
            )}
          >
            <div className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-40 transition">
              {mode.id === "circle" ? (
                <div className="absolute -top-24 right-[-80px] h-48 w-48 rounded-full bg-sky-500/60 blur-3xl" />
              ) : (
                <div className="absolute -top-24 right-[-80px] h-48 w-48 rounded-full bg-purple-500/60 blur-3xl" />
              )}
            </div>

            <div className="relative flex flex-col h-full gap-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg md:text-xl font-medium text-white">
                      {mode.label}
                    </h2>
                    <span className="rounded-full border border-white/10 bg-black/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-white/60">
                      {mode.id === "circle" ? "Minimal" : "Expressive"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs md:text-sm text-white/55">
                    {mode.tagline}
                  </p>
                </div>

                {mode.id === "circle" ? (
                  <div className="relative h-16 w-16 md:h-20 md:w-20 flex items-center justify-center">
                    <div className="absolute inset-0 rounded-full border border-sky-400/40 group-hover:border-sky-300/70 animate-pulse" />
                    <div className="h-6 w-6 md:h-8 md:w-8 rounded-full bg-gradient-to-br from-sky-400 to-emerald-400 shadow-lg shadow-sky-500/40 group-hover:scale-110 transition-transform" />
                  </div>
                ) : (
                  <div className="relative h-16 w-16 md:h-20 md:w-20 rounded-3xl border border-white/15 bg-gradient-to-br from-purple-500/40 via-sky-500/30 to-emerald-400/30 flex items-center justify-center overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(255,255,255,0.25),transparent_55%),radial-gradient(circle_at_80%_120%,rgba(56,189,248,0.3),transparent_55%)] opacity-80" />
                    <div className="relative flex flex-col items-center gap-1">
                      <div className="h-6 w-6 rounded-full bg-black/40 border border-white/40 flex items-center justify-center">
                        <div className="h-3 w-3 rounded-full bg-white/90" />
                      </div>
                      <div className="h-1.5 w-8 rounded-full bg-black/40 border border-white/30" />
                    </div>
                  </div>
                )}
              </div>

              <p className="text-xs md:text-sm text-white/60 leading-relaxed">
                {mode.description}
              </p>

              <div className="mt-auto flex items-center justify-between pt-2 text-[11px] md:text-xs text-white/55">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-5 items-center rounded-full border border-white/15 bg-black/40 px-2">
                    {mode.id === "circle" ? "Focus on content" : "Richer presence"}
                  </span>
                  <span className="hidden md:inline text-white/40">
                    {mode.id === "circle"
                      ? "Empfohlen für konzentriertes Arbeiten."
                      : "Empfohlen für explorative Sessions."}
                  </span>
                </div>
                <span className="inline-flex items-center gap-1 text-white/70 group-hover:text-white">
                  <span>Auswählen</span>
                  <span className="translate-x-0 group-hover:translate-x-0.5 transition-transform">
                    ↗
                  </span>
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

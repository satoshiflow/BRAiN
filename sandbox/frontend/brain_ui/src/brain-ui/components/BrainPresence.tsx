"use client";

import { useMemo } from "react";
import {
  usePresenceStore,
  type PresenceAffect
} from "@/brain-ui/state/presenceStore";
import { cn } from "@/lib/utils";

type BrainPresenceProps = {
  className?: string;
};

const AFFECT_LABELS: Record<PresenceAffect, string> = {
  neutral: "Neutral",
  alert: "Alert",
  happy: "Happy",
  thinking: "Thinking"
};

const AFFECT_STYLES: Record<
  PresenceAffect,
  { aura: string; glow: string; dot: string }
> = {
  neutral: {
    aura: "from-sky-500/40 via-cyan-500/35 to-blue-500/25",
    glow: "from-sky-400 via-cyan-400 to-blue-400",
    dot: "bg-sky-400"
  },
  alert: {
    aura: "from-red-600/40 via-red-500/35 to-red-400/25",
    glow: "from-red-500 via-red-400 to-amber-400",
    dot: "bg-red-400"
  },
  happy: {
    aura: "from-emerald-400/40 via-teal-400/35 to-amber-300/25",
    glow: "from-emerald-400 via-teal-400 to-amber-300",
    dot: "bg-emerald-400"
  },
  thinking: {
    aura: "from-purple-500/40 via-fuchsia-500/35 to-violet-400/25",
    glow: "from-purple-400 via-fuchsia-400 to-violet-400",
    dot: "bg-purple-400"
  }
};

export function BrainPresence({ className }: BrainPresenceProps) {
  const mode = usePresenceStore((s) => s.mode);
  const affect = usePresenceStore((s) => s.affect);
  const isSpeaking = usePresenceStore((s) => s.isSpeaking);

  const affectLabel = useMemo(() => AFFECT_LABELS[affect], [affect]);
  const styles = AFFECT_STYLES[affect];

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      {mode === "circle" ? (
        <div className="relative h-24 w-24 md:h-28 md:w-28">
          <div
            className={cn(
              "absolute inset-0 rounded-full bg-gradient-to-br blur-3xl opacity-80",
              styles.aura
            )}
          />
          <div className="relative h-full w-full rounded-full border border-white/15 bg-black/60 flex items-center justify-center shadow-[0_0_40px_rgba(15,23,42,0.9)]">
            <div
              className={cn(
                "h-10 w-10 md:h-12 md:w-12 rounded-full bg-gradient-to-br shadow-xl transition-transform duration-300",
                styles.glow,
                isSpeaking ? "scale-110 animate-pulse" : "scale-100"
              )}
            />
          </div>
        </div>
      ) : (
        <div className="relative h-40 w-40 md:h-48 md:w-48">
          <div
            className={cn(
              "absolute inset-0 bg-gradient-to-b blur-3xl opacity-80",
              styles.aura
            )}
          />
          <div className="relative h-full w-full rounded-[32px] border border-white/10 bg-gradient-to-b from-black/60 via-slate-900/80 to-black/90 overflow-hidden flex items-center justify-center">
            <div className="relative flex flex-col items-center gap-4">
              <div
                className={cn(
                  "h-24 w-24 rounded-full bg-gradient-to-b opacity-90",
                  styles.glow
                )}
              />
              <div className="h-1.5 w-20 rounded-full bg-black/40 border border-white/10" />
            </div>
          </div>
        </div>
      )}

      <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
        <div className="inline-flex items-center gap-1 rounded-full border border-white/15 bg-black/80 px-2 py-0.5 text-[10px] text-white/70">
          <span className={cn("h-1.5 w-1.5 rounded-full", styles.dot)} />
          <span>{affectLabel}</span>
        </div>
        {isSpeaking && (
          <div className="inline-flex items-center gap-1 rounded-full border border-emerald-400/40 bg-emerald-500/25 px-2 py-0.5 text-[10px] text-emerald-100">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Speaking</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default BrainPresence;

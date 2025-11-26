"use client";

import { cn } from "@/lib/utils";
import { usePresenceStore } from "@/brain-ui/state/presenceStore";

type Props = {
  className?: string;
};

export function CanvasPanel({ className }: Props) {
  const isCanvasOpen = usePresenceStore((s) => s.isCanvasOpen);
  const activeTab = usePresenceStore((s) => s.activeCanvasTab);
  const setActiveTab = usePresenceStore((s) => s.setActiveCanvasTab);

  const panelContent = (
    <div
      className={cn(
        "flex flex-col h-full border-l border-white/5 bg-black/40",
        className
      )}
    >
      <header className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <span className="text-xs font-medium text-white/70">Canvas</span>
        <div className="flex gap-4 text-[11px]">
          <button
            onClick={() => setActiveTab("documents")}
            className={cn(
              "pb-1 border-b-2",
              activeTab === "documents"
                ? "border-sky-400 text-white"
                : "border-transparent text-white/50"
            )}
          >
            Documents
          </button>
          <button
            onClick={() => setActiveTab("tools")}
            className={cn(
              "pb-1 border-b-2",
              activeTab === "tools"
                ? "border-sky-400 text-white"
                : "border-transparent text-white/50"
            )}
          >
            Tools
          </button>
        </div>
      </header>

      <div className="flex-1 p-4 text-xs text-white/60 space-y-3 overflow-y-auto">
        <p className="text-white/70">
          This is your Canvas. Later we&apos;ll show documents, tools, and
          multi-step reasoning here.
        </p>
        <div className="rounded-2xl border border-dashed border-white/10 p-3">
          <p className="mb-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
            Placeholder
          </p>
          <p>
            Connect BRAiN Missions, files and tools to see rich context next to
            the conversation.
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <div className="hidden lg:block w-72 xl:w-80">{panelContent}</div>

      <div
        className={cn(
          "lg:hidden fixed left-0 right-0 bottom-0 z-40 transition-transform duration-300",
          isCanvasOpen ? "translate-y-0" : "translate-y-[80%]"
        )}
      >
        <div className="mx-3 mb-3 rounded-3xl border border-white/10 bg-black/90 backdrop-blur-xl overflow-hidden h-64">
          {panelContent}
        </div>
      </div>
    </>
  );
}

export default CanvasPanel;

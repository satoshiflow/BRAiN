"use client";

import { cn } from "@/lib/utils";

const MOCK_THREADS = [
  "agent_scheduler.py",
  "Brain API Design",
  "UI Mockup Chat"
];

type Props = {
  className?: string;
};

export function ChatSidebar({ className }: Props) {
  return (
    <aside
      className={cn(
        "hidden md:flex flex-col w-56 xl:w-64 border-r border-white/5 bg-black/40",
        className
      )}
    >
      <div className="px-4 py-4 flex items-center justify-between border-b border-white/5">
        <button className="inline-flex items-center justify-center h-8 w-8 rounded-xl bg-white/5 border border-white/10 text-xl leading-none">
          +
        </button>
        <span className="text-xs text-white/50">New chat</span>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {MOCK_THREADS.map((title) => (
          <button
            key={title}
            className="w-full text-left px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-transparent hover:border-white/10 text-[13px] text-white/80"
          >
            {title}
          </button>
        ))}
      </div>

      <div className="border-t border-white/5 px-3 py-3 text-xs text-white/50 flex items-center justify-between">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Default
        </span>
        <span>online</span>
      </div>
    </aside>
  );
}

export default ChatSidebar;

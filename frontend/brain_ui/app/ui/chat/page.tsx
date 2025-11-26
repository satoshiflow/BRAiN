"use client";

import ChatSidebar from "@/brain-ui/components/ChatSidebar";
import ChatShell from "@/brain-ui/components/ChatShell";
import CanvasPanel from "@/brain-ui/components/CanvasPanel";

export default function ChatPage() {
  return (
    <div className="h-[calc(100vh-4rem)] md:h-[calc(100vh-5rem)] flex rounded-3xl border border-white/10 bg-black/40 overflow-hidden shadow-[0_0_80px_rgba(15,23,42,0.9)]">
      <ChatSidebar />
      <ChatShell />
      <CanvasPanel />
    </div>
  );
}

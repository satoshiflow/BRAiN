"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import BrainPresence from "@/brain-ui/components/BrainPresence";
import { usePresenceStore } from "@/brain-ui/state/presenceStore";
import { sendChat, type ChatMessage } from "@/lib/brainApi";

type Message = {
  id: number;
  from: "user" | "brain";
  text: string;
};

const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    from: "brain",
    text: "Please go ahead and upload the file here."
  },
  {
    id: 2,
    from: "brain",
    text: "I created an initial user interface mockup."
  }
];

export function ChatShell() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const openCanvas = usePresenceStore((s) => s.openCanvas);
  const setAffect = usePresenceStore((s) => s.setAffect);
  const setSpeaking = usePresenceStore((s) => s.setSpeaking);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput("");

    const userMsg: Message = {
      id: Date.now(),
      from: "user",
      text
    };
    setMessages((prev) => [...prev, userMsg]);

    setAffect("thinking");
    setSending(true);
    setSpeaking(true);

    try {

    const systemMessage: ChatMessage = {
      role: "system",
      content: "You are BRAiN, the multi-agent controller...",
    };

    const history: ChatMessage[] = messages.map(
      (m): ChatMessage => ({
        role: m.from === "user" ? "user" : "assistant",
        content: m.text ?? "",
    })
  );
      const res = await sendChat(history);

      const brainMsg: Message = {
        id: Date.now() + 1,
        from: "brain",
        text: res.reply
      };
      setMessages((prev) => [...prev, brainMsg]);
      setAffect("happy");
    } catch (e) {
      const brainMsg: Message = {
        id: Date.now() + 2,
        from: "brain",
        text: "I could not reach my backend just now."
      };
      setMessages((prev) => [...prev, brainMsg]);
      setAffect("alert");
    } finally {
      setSending(false);
      setSpeaking(false);
    }
  };

  return (
    <section className="flex-1 flex flex-col h-full">
      <header className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-white/70">BRAiN</span>
          <span className="text-[11px] text-white/45">
            Immersive conversational interface
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => openCanvas()}
            className="lg:hidden inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-white/70"
          >
            Canvas
          </button>
        </div>
      </header>

      <div className="px-4 pt-6 pb-4 flex justify-center">
        <BrainPresence />
      </div>

      <div className="flex-1 px-4 pb-4 overflow-y-auto space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex",
              msg.from === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-2xl px-4 py-2 text-sm",
                msg.from === "user"
                  ? "bg-sky-500/20 text-white border border-sky-500/40"
                  : "bg-white/5 text-white/90 border border-white/10"
              )}
            >
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      <div className="px-4 pb-4">
        <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-black/60 px-3 py-2">
          <button
            type="button"
            className="h-8 w-8 rounded-xl border border-white/10 bg-white/5 text-xs text-white/60"
          >
            📎
          </button>
          <input
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/40 focus:outline-none"
            placeholder="Enter a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={sending}
            className="h-8 w-8 rounded-xl bg-sky-500/80 hover:bg-sky-400 text-white text-sm flex items-center justify-center disabled:opacity-60"
          >
            ➤
          </button>
        </div>
      </div>
    </section>
  );
}

export default ChatShell;

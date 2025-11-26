"use client"

import { useState } from "react"
import type { ChatMessage } from "@/lib/llm"

type ChatEntry = {
  id: string
  role: "user" | "assistant"
  content: string
}

export function AxeChatDock() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      id: "assistant-hello",
      role: "assistant",
      content:
        "👋 Hey Olaf, ich bin AXE. Frag mich alles rund um das BRAIN Control Deck – später mit echtem Kontext aus deinem Backend.",
    },
  ])
  const [error, setError] = useState<string | null>(null)

  async function sendMessage(e?: React.FormEvent) {
    e?.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setError(null)

    const userMessage: ChatEntry = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const historyForBackend: ChatMessage[] = messages.map((m) => ({
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
      }))

      const res = await fetch("/api/axe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: historyForBackend,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.error || `HTTP ${res.status}`)
      }

      const data = (await res.json()) as { reply: string }

      const assistantMessage: ChatEntry = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.reply,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: any) {
      console.error("AXE client error:", err)
      setError(
        "AXE ist gerade nicht erreichbar. Läuft Ollama auf 127.0.0.1:11434 und ist ein Modell geladen?"
      )
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 rounded-full bg-gradient-to-br from-brain-goldStrong to-brain-gold px-4 py-3 text-sm font-semibold text-black shadow-brain-glow flex items-center gap-2"
      >
        <span>AXE</span>
        <span className="text-[0.6rem] uppercase tracking-[0.3em]">
          Assist
        </span>
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-[380px] max-w-[92vw] rounded-3xl border border-brain-gold/40 bg-brain-panel/95 shadow-brain-glow backdrop-blur">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div>
          <div className="text-xs uppercase tracking-[0.25em] text-brain-goldStrong">
            Axe
          </div>
          <div className="text-[0.7rem] text-slate-400">
            Lokaler BRAIN Assistent (Ollama)
          </div>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="text-xs text-slate-400 hover:text-slate-100"
        >
          ✕
        </button>
      </div>

      <div className="px-4 py-3 space-y-3 text-sm max-h-[320px] overflow-y-auto">
        {messages.map((m) => (
          <div
            key={m.id}
            className={
              m.role === "user"
                ? "ml-auto max-w-[85%] rounded-2xl bg-brain-gold/15 px-3 py-2 text-slate-50"
                : "mr-auto max-w-[90%] rounded-2xl bg-black/40 px-3 py-2 text-slate-200"
            }
          >
            {m.content}
          </div>
        ))}

        {loading && (
          <div className="mr-auto max-w-[80%] rounded-2xl bg-black/50 px-3 py-2 text-xs text-slate-400">
            Axe denkt nach …
          </div>
        )}

        {error && (
          <div className="text-xs text-red-400 bg-red-950/40 border border-red-700/40 rounded-2xl px-3 py-2">
            {error}
          </div>
        )}
      </div>

      <form
        onSubmit={sendMessage}
        className="px-4 py-3 border-t border-white/5"
      >
        <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-black/40 px-3 py-2">
          <input
            className="flex-1 bg-transparent text-xs text-slate-100 placeholder:text-slate-500 outline-none"
            placeholder="Frag Axe z.B.: Erklär mir das Mission Deck."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="text-xs uppercase tracking-[0.2em] text-brain-goldStrong disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

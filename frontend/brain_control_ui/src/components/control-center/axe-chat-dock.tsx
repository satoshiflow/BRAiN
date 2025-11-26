"use client"

import { useState } from "react"

export function AxeChatDock() {
  const [open, setOpen] = useState(false)

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
            Kontext-sensitiver BRAIN Assist (UI-Dummy)
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
        <div className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-500">
          Demo-Modus
        </div>
        <div className="rounded-2xl bg-black/40 px-3 py-2 text-slate-200">
          👋 Hey Olaf, ich bin <span className="text-brain-gold">Axe</span>.{" "}
          Aktuell bin ich nur ein visuelles Dummy-Modul ohne LLM-Anbindung.
        </div>
        <div className="rounded-2xl bg-black/40 px-3 py-2 text-slate-200">
          Nächster Schritt: eine lokale API-Route <code>/api/axe</code> und
          eine Verbindung zu Ollama oder anderen LLMs.
        </div>
        <div className="rounded-2xl bg-brain-gold/10 px-3 py-2 text-slate-100">
          Du kannst dieses UI-Element bereits in deinem Control Deck nutzen und
          später nahtlos die echte KI dahinter schalten.
        </div>
      </div>

      <div className="px-4 py-3 border-t border-white/5">
        <div className="rounded-2xl border border-white/10 bg-black/40 px-3 py-2 text-xs text-slate-500">
          Eingabe ist deaktiviert, bis das Backend verbunden ist.
        </div>
      </div>
    </div>
  )
}

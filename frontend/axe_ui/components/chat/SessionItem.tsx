"use client";

import { useState } from "react";
import type { AxeSessionSummary } from "@/lib/contracts";

type SessionItemProps = {
  session: AxeSessionSummary;
  active: boolean;
  onSelect: (sessionId: string) => void;
  onRename: (sessionId: string, title: string) => Promise<void>;
  onDelete: (sessionId: string) => Promise<void>;
};

export function SessionItem({ session, active, onSelect, onRename, onDelete }: SessionItemProps) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(session.title);

  return (
    <div
      className={`group rounded-lg border px-3 py-2 transition-all ${
        active
          ? "axe-ring border-cyan-400/45 bg-cyan-500/10"
          : "border-slate-800 bg-slate-950/40 hover:border-cyan-400/20 hover:bg-slate-900/80"
      }`}
    >
      {editing ? (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            const trimmed = title.trim();
            if (!trimmed) {
              return;
            }
            await onRename(session.id, trimmed);
            setEditing(false);
          }}
          className="space-y-2"
        >
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-100"
            maxLength={200}
            autoFocus
          />
          <div className="flex gap-2">
            <button type="submit" className="text-xs text-cyan-300 hover:text-cyan-200">
              Save
            </button>
            <button type="button" className="text-xs text-slate-400 hover:text-slate-300" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          <button type="button" className="w-full text-left" onClick={() => onSelect(session.id)}>
            <p className="truncate text-sm text-slate-100">{session.title}</p>
            {session.preview && <p className="mt-1 truncate text-xs text-slate-400">{session.preview}</p>}
          </button>
          <div
            className={`mt-2 items-center gap-2 text-xs ${
              active ? "flex" : "flex sm:hidden sm:group-hover:flex"
            }`}
          >
            <button
              type="button"
              onClick={() => {
                setTitle(session.title);
                setEditing(true);
              }}
              className="text-cyan-300/80 hover:text-cyan-200"
            >
              Rename
            </button>
            <button
              type="button"
              onClick={async () => {
                if (window.confirm("Delete this chat session?")) {
                  await onDelete(session.id);
                }
              }}
              className="text-rose-300/80 hover:text-rose-200"
            >
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  );
}

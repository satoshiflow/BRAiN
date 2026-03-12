"use client";

import type { AxeSessionSummary } from "@/lib/contracts";
import { SessionItem } from "@/components/chat/SessionItem";

type SessionGroupProps = {
  label: string;
  sessions: AxeSessionSummary[];
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onRename: (sessionId: string, title: string) => Promise<void>;
  onDelete: (sessionId: string) => Promise<void>;
};

export function SessionGroup({
  label,
  sessions,
  activeSessionId,
  onSelect,
  onRename,
  onDelete,
}: SessionGroupProps) {
  if (sessions.length === 0) {
    return null;
  }

  return (
    <section>
      <h3 className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</h3>
      <div className="space-y-2">
        {sessions.map((session) => (
          <SessionItem
            key={session.id}
            session={session}
            active={session.id === activeSessionId}
            onSelect={onSelect}
            onRename={onRename}
            onDelete={onDelete}
          />
        ))}
      </div>
    </section>
  );
}

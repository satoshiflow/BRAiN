"use client";

import { useState } from "react";
import { Menu, Plus } from "lucide-react";
import type { GroupedSessions } from "@/hooks/useChatSessions";
import { SessionGroup } from "@/components/chat/SessionGroup";
import { Sheet, SheetContent } from "@/components/ui/sheet";

type ChatSidebarProps = {
  groupedSessions: GroupedSessions;
  activeSessionId: string | null;
  loading: boolean;
  onSelectSession: (sessionId: string) => Promise<unknown>;
  onRenameSession: (sessionId: string, title: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onCreateSession: () => Promise<void>;
};

function SidebarContent({
  groupedSessions,
  activeSessionId,
  loading,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  onCreateSession,
}: ChatSidebarProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-800 p-4">
        <button
          type="button"
          onClick={() => void onCreateSession()}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 transition-colors hover:bg-slate-700"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-3">
        {loading && <p className="text-xs text-slate-400">Loading sessions...</p>}
        <SessionGroup
          label="Today"
          sessions={groupedSessions.today}
          activeSessionId={activeSessionId}
          onSelect={(id) => void onSelectSession(id)}
          onRename={(id, title) => onRenameSession(id, title)}
          onDelete={(id) => onDeleteSession(id)}
        />
        <SessionGroup
          label="Yesterday"
          sessions={groupedSessions.yesterday}
          activeSessionId={activeSessionId}
          onSelect={(id) => void onSelectSession(id)}
          onRename={(id, title) => onRenameSession(id, title)}
          onDelete={(id) => onDeleteSession(id)}
        />
        <SessionGroup
          label="Older"
          sessions={groupedSessions.older}
          activeSessionId={activeSessionId}
          onSelect={(id) => void onSelectSession(id)}
          onRename={(id, title) => onRenameSession(id, title)}
          onDelete={(id) => onDeleteSession(id)}
        />
      </div>
    </div>
  );
}

export function ChatSidebar(props: ChatSidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="mb-3 inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 lg:hidden"
      >
        <Menu className="h-4 w-4" />
        Sessions
      </button>

      <aside className="hidden h-full w-72 flex-none overflow-hidden rounded-lg border border-slate-800 bg-slate-900 lg:block">
        <SidebarContent {...props} />
      </aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[88vw] max-w-sm border-slate-800 bg-slate-900 p-0">
          <SidebarContent {...props} />
        </SheetContent>
      </Sheet>
    </>
  );
}

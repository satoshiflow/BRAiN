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
  showMobileTrigger?: boolean;
  showDesktopRail?: boolean;
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
      <div className="border-b border-cyan-400/15 p-4">
        <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-cyan-300/70">Memory Lane</p>
        <button
          type="button"
          onClick={() => void onCreateSession()}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-400/35 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100 transition-colors hover:bg-cyan-500/20"
        >
          <Plus className="h-4 w-4" />
          New Intent Thread
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-3">
        {loading && <p className="text-xs text-cyan-200/70">Syncing memory threads...</p>}
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
  const showMobileTrigger = props.showMobileTrigger ?? true;
  const showDesktopRail = props.showDesktopRail ?? true;

  return (
    <>
      {showMobileTrigger && (
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="mb-3 ml-auto inline-flex items-center gap-2 rounded-lg border border-cyan-400/35 bg-slate-900/80 px-3 py-2 text-sm text-cyan-100 lg:hidden"
        >
          <Menu className="h-4 w-4" />
          Memory
        </button>
      )}

      {showDesktopRail && (
        <aside className="axe-panel hidden h-full w-72 flex-none overflow-hidden rounded-xl lg:block">
          <SidebarContent {...props} />
        </aside>
      )}

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[88vw] max-w-sm axe-panel border-cyan-500/20 p-0">
          <SidebarContent {...props} />
        </SheetContent>
      </Sheet>
    </>
  );
}

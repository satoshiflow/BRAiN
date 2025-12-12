"use client";

export default function Topbar() {
  return (
    <header className="border-b border-border/50 bg-secondary/20 backdrop-blur-md px-6 py-4 flex justify-between items-center">
      <h1 className="text-lg tracking-wider text-muted-foreground uppercase">
        BRAiN Control Deck
      </h1>

      <div className="flex gap-3 items-center">
        <span className="brain-dot brain-dot-online" />
        <span className="text-xs text-muted-foreground">System Online</span>
      </div>
    </header>
  );
}

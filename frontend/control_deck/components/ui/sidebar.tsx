// frontend/brain_control_ui/src/components/ui/sidebar.tsx
"use client";

import * as React from "react";
import { PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";

type SidebarContextValue = {
  collapsed: boolean;
  toggle: () => void;
};

const SidebarContext = React.createContext<SidebarContextValue | undefined>(
  undefined
);

export function useSidebar() {
  const ctx = React.useContext(SidebarContext);
  if (!ctx) {
    throw new Error("useSidebar must be used within <SidebarProvider>");
  }
  return ctx;
}

interface SidebarProviderProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
  defaultCollapsed?: boolean;
}

export function SidebarProvider({
  children,
  style,
  defaultCollapsed = false,
}: SidebarProviderProps) {
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed);

  const value = React.useMemo(
    () => ({
      collapsed,
      toggle: () => setCollapsed((v) => !v),
    }),
    [collapsed]
  );

  return (
    <SidebarContext.Provider value={value}>
      <div
        data-sidebar-collapsed={collapsed ? "true" : "false"}
        className="flex min-h-screen bg-background text-foreground"
        style={style}
      >
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

interface SidebarInsetProps extends React.HTMLAttributes<HTMLDivElement> {}

export function SidebarInset({ className, ...props }: SidebarInsetProps) {
  return (
    <div
      className={cn(
        "flex flex-1 flex-col bg-gradient-to-b from-background via-background to-background/95",
        className
      )}
      {...props}
    />
  );
}

interface SidebarTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export function SidebarTrigger({
  className,
  ...props
}: SidebarTriggerProps) {
  const { toggle } = useSidebar();

  return (
    <button
      type="button"
      onClick={toggle}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-background/80 text-muted-foreground shadow-sm hover:bg-muted/60",
        className
      )}
      aria-label="Toggle sidebar"
      {...props}
    >
      <PanelLeft className="h-4 w-4" />
    </button>
  );
}

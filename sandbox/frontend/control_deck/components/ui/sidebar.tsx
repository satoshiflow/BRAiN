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

// Additional sidebar components for app-sidebar compatibility
export function Sidebar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <aside className={cn("flex h-screen w-64 flex-col border-r bg-background", className)} {...props} />;
}

export function SidebarHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-2 p-4 border-b", className)} {...props} />;
}

export function SidebarContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex-1 overflow-auto p-4", className)} {...props} />;
}

export function SidebarFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4 border-t", className)} {...props} />;
}

export function SidebarRail({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("absolute right-0 top-0 h-full w-px bg-border", className)} {...props} />;
}

export function SidebarGroup({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-2", className)} {...props} />;
}

export function SidebarGroupLabel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-2 py-1 text-xs font-semibold text-muted-foreground", className)} {...props} />;
}

export function SidebarMenu({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) {
  return <ul className={cn("flex flex-col gap-1", className)} {...props} />;
}

export function SidebarMenuItem({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) {
  return <li className={cn("", className)} {...props} />;
}

export function SidebarMenuButton({ className, asChild, tooltip, ...props }: React.HTMLAttributes<HTMLButtonElement> & { asChild?: boolean; tooltip?: string }) {
  const Comp = asChild ? "div" : "button";
  return <Comp className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted", className)} title={tooltip} {...(props as any)} />;
}

export function SidebarMenuSub({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) {
  return <ul className={cn("ml-4 flex flex-col gap-1 border-l pl-2", className)} {...props} />;
}

export function SidebarMenuSubItem({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) {
  return <li className={cn("", className)} {...props} />;
}

export function SidebarMenuSubButton({ className, asChild, tooltip, ...props }: React.HTMLAttributes<HTMLButtonElement> & { asChild?: boolean; tooltip?: string }) {
  const Comp = asChild ? "div" : "button";
  return <Comp className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-muted", className)} title={tooltip} {...(props as any)} />;
}

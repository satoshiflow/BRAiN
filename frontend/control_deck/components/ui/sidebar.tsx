"use client";

import * as React from "react";

type WithChildren<T = unknown> = T & {
  children?: React.ReactNode;
};

function cn(...values: Array<string | boolean | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function Sidebar({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <aside
      className={cn(
        "flex h-screen w-64 flex-col border-r border-slate-800 bg-slate-950",
        className,
      )}
    >
      {children}
    </aside>
  );
}

export function SidebarHeader({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <div
      className={cn(
        "flex items-center gap-3 border-b border-slate-800 px-4 py-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SidebarContent({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <div
      className={cn(
        "flex-1 overflow-y-auto px-2 py-3 space-y-2",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SidebarFooter({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <div
      className={cn(
        "border-t border-slate-800 px-3 py-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SidebarRail(): JSX.Element {
  return <></>;
}

export function SidebarGroup({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return <div className={cn("space-y-1", className)}>{children}</div>;
}

export function SidebarGroupLabel({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <div
      className={cn(
        "px-3 text-xs font-semibold uppercase tracking-wide text-slate-500",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SidebarMenu({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return <ul className={cn("mt-1 space-y-1", className)}>{children}</ul>;
}

export function SidebarMenuItem({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return <li className={cn("text-sm", className)}>{children}</li>;
}

export function SidebarMenuButton({
  className,
  children,
  tooltip,
}: WithChildren<{ className?: string; tooltip?: string }>): JSX.Element {
  return (
    <button
      type="button"
      title={tooltip}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left text-slate-200 hover:bg-slate-800",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function SidebarMenuSub({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <ul className={cn("mt-1 space-y-1 pl-6 text-xs text-slate-300", className)}>
      {children}
    </ul>
  );
}

export function SidebarMenuSubItem({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return <li className={cn(className)}>{children}</li>;
}

export function SidebarMenuSubButton({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <button
      type="button"
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-2 py-1 hover:bg-slate-800",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function SidebarProvider({
  children,
  defaultOpen = true,
}: WithChildren<{ defaultOpen?: boolean }>): JSX.Element {
  const [open, setOpen] = React.useState(defaultOpen);
  return <>{children}</>;
}

export function SidebarInset({
  className,
  children,
}: WithChildren<{ className?: string }>): JSX.Element {
  return (
    <main className={cn("flex flex-1 flex-col bg-slate-950", className)}>
      {children}
    </main>
  );
}

export function SidebarTrigger({
  className,
}: {
  className?: string;
}): JSX.Element {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-800 hover:text-slate-100",
        className,
      )}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <line x1="4" x2="20" y1="12" y2="12" />
        <line x1="4" x2="20" y1="6" y2="6" />
        <line x1="4" x2="20" y1="18" y2="18" />
      </svg>
    </button>
  );
}
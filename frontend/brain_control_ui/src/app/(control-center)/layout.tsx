// frontend/brain_control_ui/src/app/(control-center)/layout.tsx
import type { ReactNode, CSSProperties } from "react";
import {
  SidebarProvider,
  SidebarInset,
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { SiteHeader } from "@/components/site-header";

export default function ControlCenterLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "18rem",
          "--header-height": "3.5rem",
        } as CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <main className="flex-1 px-4 pb-6 pt-4 lg:px-8 lg:pt-6">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

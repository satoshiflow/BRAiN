"use client";

import { ChevronDown } from "lucide-react";

import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

type Team = {
  name: string;
  logo?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  plan?: string;
};

export function TeamSwitcher({ teams }: { teams: Team[] }) {
  const active = teams[0];

  const Logo = active.logo;

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton className="justify-between">
          <div className="flex items-center gap-2">
            {Logo && <Logo className="h-4 w-4" />}
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-neutral-100">
                {active.name}
              </span>
              {active.plan && (
                <span className="text-[10px] text-neutral-400">
                  {active.plan}
                </span>
              )}
            </div>
          </div>
          <ChevronDown className="h-3 w-3 text-neutral-500" />
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
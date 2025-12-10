"use client";

import Image from "next/image";

import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

type User = {
  name: string;
  email: string;
  avatar?: string;
};

export function NavUser({ user }: { user: User }) {
  const initial = user.name?.charAt(0)?.toUpperCase() ?? "B";

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton className="gap-2">
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-emerald-600 text-xs font-semibold text-white">
            {user.avatar ? (
              <Image
                src={user.avatar}
                alt={user.name}
                width={32}
                height={32}
                className="h-8 w-8 rounded-full object-cover"
              />
            ) : (
              <span>{initial}</span>
            )}
          </div>
          <div className="flex flex-col items-start">
            <span className="text-xs font-medium text-neutral-100">
              {user.name}
            </span>
            <span className="text-[10px] text-neutral-400">
              {user.email}
            </span>
          </div>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
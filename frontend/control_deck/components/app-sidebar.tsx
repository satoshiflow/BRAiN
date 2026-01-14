"use client";

import * as React from "react";
import {
  Activity,
  Bot,
  Command,
  Globe,
  LayoutDashboard,
  Map,
  Shield,
  Settings2,
  Workflow,
  Radio,
  Cpu,
  Dna,
  Database,
  Coins,
  GraduationCap,
  Briefcase,
  Scale,
  Users,
  Boxes,
} from "lucide-react";

import { NavMain } from "@/components/nav-main";
import { NavUser } from "@/components/nav-user";
import { TeamSwitcher } from "@/components/team-switcher";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";

const data = {
  user: {
    name: "BRAiN Admin",
    email: "admin@brain.local",
    avatar: "/avatars/shadcn.jpg",
  },
  teams: [
    {
      name: "BRAiN Core",
      logo: Command,
      plan: "Local",
    },
  ],
  navMain: [
    {
      title: "Dashboard",
      url: "/",
      icon: LayoutDashboard,
      isActive: false,
      items: [
        {
          title: "System Overview",
          url: "/",
        },
      ],
    },
    {
      title: "Core",
      url: "/core",
      icon: Workflow,
      isActive: false,
      items: [
        {
          title: "Modules",
          url: "/core/modules",
        },
        {
          title: "System Agents",
          url: "/core/agents",
        },
      ],
    },
    {
      title: "Missions",
      url: "/missions",
      icon: Map,
      isActive: false,
      items: [
        {
          title: "Overview",
          url: "/missions",
        },
        {
          title: "History",
          url: "/missions/history",
        },
      ],
    },
    {
      title: "NeuroRail",
      url: "/neurorail",
      icon: Activity,
      isActive: false,
      items: [
        {
          title: "Trace Explorer",
          url: "/neurorail/trace-explorer",
        },
        {
          title: "Health Matrix",
          url: "/neurorail/health-matrix",
        },
      ],
    },
    {
      title: "Agents",
      url: "/agents",
      icon: Bot,
      isActive: false,
      items: [
        {
          title: "Overview",
          url: "/agents",
        },
        {
          title: "New Agent",
          url: "/agents/new",
        },
      ],
    },
    {
      title: "WebGenesis",
      url: "/webgenesis",
      icon: Globe,
      isActive: false,
      items: [
        {
          title: "Sites",
          url: "/webgenesis",
        },
        {
          title: "Create New Site",
          url: "/webgenesis/new",
        },
      ],
    },
    {
      title: "Immune & Threats",
      url: "/immune",
      icon: Shield,
      isActive: false,
      items: [
        {
          title: "Threats",
          url: "/immune",
        },
        {
          title: "Events",
          url: "/immune/events",
        },
      ],
    },
    {
      title: "System Monitoring",
      url: "/telemetry",
      icon: Radio,
      isActive: false,
      items: [
        {
          title: "Telemetry",
          url: "/telemetry",
        },
        {
          title: "Hardware",
          url: "/hardware",
        },
      ],
    },
    {
      title: "AI Evolution",
      url: "/dna",
      icon: Dna,
      isActive: false,
      items: [
        {
          title: "DNA Evolution",
          url: "/dna",
        },
        {
          title: "Knowledge Graph",
          url: "/knowledge-graph",
        },
      ],
    },
    {
      title: "Governance",
      url: "/policy-engine",
      icon: Scale,
      isActive: false,
      items: [
        {
          title: "Policy Engine",
          url: "/policy-engine",
        },
        {
          title: "Constitutional Agents",
          url: "/constitutional",
        },
      ],
    },
    {
      title: "Resources",
      url: "/credits",
      icon: Coins,
      isActive: false,
      items: [
        {
          title: "Credits System",
          url: "/credits",
        },
      ],
    },
    {
      title: "Education",
      url: "/courses",
      icon: GraduationCap,
      isActive: false,
      items: [
        {
          title: "Course Factory",
          url: "/courses",
        },
        {
          title: "Business Factory",
          url: "/business",
        },
      ],
    },
    {
      title: "Fleet Management",
      url: "/fleet-management",
      icon: Boxes,
      isActive: false,
      items: [
        {
          title: "Fleet Overview",
          url: "/fleet-management",
        },
      ],
    },
    {
      title: "Settings",
      url: "/settings",
      icon: Settings2,
      isActive: false,
      items: [
        {
          title: "System",
          url: "/settings",
        },
        {
          title: "API Keys",
          url: "/settings/api",
        },
        {
          title: "Identity",
          url: "/settings/identity",
        },
      ],
    },
  ],
};

export function AppSidebar(
  props: React.ComponentProps<typeof Sidebar>,
): JSX.Element {
  return (
    <Sidebar {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
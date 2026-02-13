"use client";

import * as React from "react";
import {
  Activity,
  Bot,
  Code,
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
  Wrench,
  Heart,
  GitBranch,
  UserCog,
  AlertTriangle,
  PlusCircle,
  Network,
  Clock,
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
      title: "Monitoring & Überwachung",
      url: "#",
      icon: Activity,
      isActive: true,
      items: [
        {
          title: "System Dashboard",
          url: "/dashboard",
        },
        {
          title: "System Health",
          url: "/health",
        },
        {
          title: "Missions Overview",
          url: "/missions",
        },
        {
          title: "Mission History",
          url: "/missions/history",
        },
        {
          title: "Agent Management",
          url: "/core/agents",
        },
        {
          title: "Supervisor Panel",
          url: "/supervisor",
        },
        {
          title: "Telemetry",
          url: "/telemetry",
        },
        {
          title: "Hardware Resources",
          url: "/hardware",
        },
        {
          title: "Immune System",
          url: "/immune",
        },
        {
          title: "Threat Events",
          url: "/immune/events",
        },
        {
          title: "NeuroRail Trace",
          url: "/neurorail/trace-explorer",
        },
        {
          title: "NeuroRail Health",
          url: "/neurorail/health-matrix",
        },
        {
          title: "Fleet Management",
          url: "/fleet-management",
        },
      ],
    },
    {
      title: "Development",
      url: "#",
      icon: Code,
      isActive: false,
      items: [
        {
          title: "Fred Bridge",
          url: "/fred-bridge",
        },
        {
          title: "AXE Widget",
          url: "/axe-widget",
        },
        {
          title: "DNA Evolution",
          url: "/dna",
        },
      ],
    },
    {
      title: "BRAiN Einstellungen",
      url: "#",
      icon: Settings2,
      isActive: false,
      items: [
        {
          title: "System Settings",
          url: "/settings",
        },
        {
          title: "API Configuration",
          url: "/settings/api",
        },
        {
          title: "Identity & Access",
          url: "/settings/identity",
        },
        {
          title: "LLM Configuration",
          url: "/settings/llm",
        },
        {
          title: "Policy Engine",
          url: "/policy-engine",
        },
        {
          title: "Credits System",
          url: "/credits",
        },
        {
          title: "Core Modules",
          url: "/core/modules",
        },
      ],
    },
    {
      title: "Tools/Desktop",
      url: "#",
      icon: Wrench,
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
        {
          title: "WebGenesis Sites",
          url: "/webgenesis",
        },
        {
          title: "Create New Site",
          url: "/webgenesis/new",
        },
        {
          title: "Create Agent",
          url: "/agents/new",
        },
        {
          title: "Constitutional Agents",
          url: "/constitutional",
        },
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
"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Bot,
  Puzzle,
  Eye,
  Plus,
  ArrowRight,
  Cpu,
  Activity,
  Users,
} from "lucide-react";

const agentFeatures = [
  {
    title: "Skills Library",
    description: "PicoClaw-style skills for extending agent capabilities",
    icon: Puzzle,
    href: "/agents/skills",
    count: "View all skills",
    color: "bg-blue-500/10 text-blue-400",
  },
  {
    title: "Supervisor",
    description: "Monitor and control active agent instances",
    icon: Eye,
    href: "/agents/supervisor",
    count: "Live monitoring",
    color: "bg-purple-500/10 text-purple-400",
  },
];

const stats = [
  { label: "Active Agents", value: "0", icon: Bot },
  { label: "Available Skills", value: "—", icon: Puzzle },
  { label: "Running Tasks", value: "0", icon: Activity },
  { label: "Agent Pool", value: "—", icon: Users },
];

export default function AgentsPage() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agent Registry</h1>
          <p className="text-muted-foreground">
            Manage agents, skills, and supervision
          </p>
        </div>
        <Button className="shrink-0 gap-2">
          <Plus className="h-4 w-4" />
          Deploy Agent
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="border-border/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
                <div className="rounded-lg bg-secondary p-2">
                  <stat.icon className="h-5 w-5 text-muted-foreground" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Features Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {agentFeatures.map((feature) => (
          <Card
            key={feature.title}
            className="group cursor-pointer border-border/50 transition-colors hover:border-primary/50"
            onClick={() => router.push(feature.href)}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`rounded-lg p-2 ${feature.color}`}>
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </div>
                </div>
                <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </div>
            </CardHeader>
            <CardContent>
              <Badge variant="secondary">{feature.count}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Coming Soon */}
      <Card className="border-border/50 border-dashed">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-secondary p-2">
              <Cpu className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <CardTitle className="text-lg">Custom Agents</CardTitle>
              <CardDescription>
                Build and deploy custom autonomous agents
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Define agent personalities, capabilities, and behavior using skills
            from the library.
          </p>
          <Button variant="outline" className="mt-4" disabled>
            Coming Soon
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

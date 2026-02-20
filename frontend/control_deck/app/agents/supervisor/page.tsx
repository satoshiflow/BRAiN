"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Eye, Activity, AlertCircle } from "lucide-react";

export default function SupervisorPage() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => router.push("/agents")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Supervisor</h1>
          <p className="text-sm text-muted-foreground">
            Monitor and control active agent instances
          </p>
        </div>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-purple-500/10 p-2">
              <Eye className="h-5 w-5 text-purple-400" />
            </div>
            <div>
              <CardTitle>Agent Monitoring</CardTitle>
              <CardDescription>
                Real-time supervision of running agents
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 rounded-lg border border-border/50 p-4">
            <Activity className="h-8 w-8 text-muted-foreground" />
            <div>
              <p className="font-medium">No active agents</p>
              <p className="text-sm text-muted-foreground">
                Deploy an agent to start monitoring
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3 rounded-lg bg-amber-500/10 p-4 text-amber-400">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="text-sm">
              <p className="font-medium">Coming Soon</p>
              <p className="text-amber-400/80">
                The Supervisor dashboard is under development. Soon you'll be able to
                view real-time agent activity, logs, and control running instances.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

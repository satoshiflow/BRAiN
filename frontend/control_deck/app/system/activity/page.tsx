"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Activity } from "lucide-react";

export default function ActivityLogPage() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => router.push("/dashboard")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Activity Log</h1>
          <p className="text-sm text-muted-foreground">
            System events and audit trail
          </p>
        </div>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/10 p-2">
              <Activity className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <CardTitle>Recent Events</CardTitle>
              <CardDescription>
                System activity history
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No recent activity to display.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

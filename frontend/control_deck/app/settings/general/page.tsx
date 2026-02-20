"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Settings } from "lucide-react";

export default function GeneralSettingsPage() {
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
          <h1 className="text-2xl font-bold tracking-tight">General Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure BRAiN system preferences
          </p>
        </div>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-secondary p-2">
              <Settings className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <CardTitle>System Configuration</CardTitle>
              <CardDescription>
                General system settings
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Settings interface coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

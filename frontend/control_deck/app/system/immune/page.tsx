"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ShieldCheck } from "lucide-react";

export default function ImmuneSystemPage() {
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
          <h1 className="text-2xl font-bold tracking-tight">Immune System</h1>
          <p className="text-sm text-muted-foreground">
            Security monitoring and threat detection
          </p>
        </div>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-500/10 p-2">
              <ShieldCheck className="h-5 w-5 text-green-400" />
            </div>
            <div>
              <CardTitle>System Status</CardTitle>
              <CardDescription>
                All systems operational
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The Immune System monitors for security threats, anomalous behavior,
            and system integrity. No issues detected.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

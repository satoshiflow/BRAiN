"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Construction, Shield } from "lucide-react";

/**
 * Governance & HITL Approvals Dashboard
 * Sprint 16: Human-in-the-loop approval workflows
 */

export default function GovernancePage() {
  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Governance
          </h1>
          <p className="text-muted-foreground mt-1">
            Human-in-the-loop approval workflows
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Construction className="h-5 w-5" />
              Under Construction
            </CardTitle>
            <CardDescription>
              Governance and HITL approval workflows are being finalized.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              This page will show pending approvals and allow authorized users
              to approve or reject actions.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

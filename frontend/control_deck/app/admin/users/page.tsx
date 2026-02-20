"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Construction } from "lucide-react";

export default function UserManagementPage() {
  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground mt-1">
            Manage users, roles, and invitations
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Construction className="h-5 w-5" />
              Under Construction
            </CardTitle>
            <CardDescription>
              This page is temporarily disabled during build optimization.
              Full user management will be available in the next deployment.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              The authentication system backend is fully operational. 
              Frontend integration is being finalized.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

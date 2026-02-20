"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, FileText, User } from "lucide-react";

export default function Dashboard() {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch("/api/auth/session");
        const data = await res.json();

        if (data?.user) {
          setSession(data);
        } else {
          router.push("/auth/signin");
        }
      } catch {
        router.push("/auth/signin");
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="text-muted-foreground">Loading BRAiN...</div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1>Dashboard</h1>
        <p className="text-muted-foreground">Welcome to BRAiN v0.3.0</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
        {/* Backend Status Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Backend Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <a
                href="http://127.0.0.1:8001/api/health"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-500 hover:text-emerald-400 transition-colors"
              >
                ✅ Running
              </a>
              <CardDescription>Health endpoint active</CardDescription>
            </div>
          </CardContent>
        </Card>

        {/* API Documentation Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Documentation</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <a
                href="http://127.0.0.1:8001/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Open Swagger UI
              </a>
              <CardDescription>Interactive API docs</CardDescription>
            </div>
          </CardContent>
        </Card>

        {/* Session Info Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Session Info</CardTitle>
            <User className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-sm">
                <span className="text-muted-foreground">User:</span>{" "}
                <span className="font-medium">{session.user?.name}</span>
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">Email:</span>{" "}
                <span className="font-medium">{session.user?.email}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {session.user?.groups?.map((group: string) => (
                  <Badge key={group} variant="secondary">
                    {group}
                  </Badge>
                )) || <Badge variant="secondary">operator</Badge>}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useState, useEffect } from "react";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  Filter,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getJSON } from "@/lib/api";

interface ThreatEvent {
  id: string;
  timestamp: string;
  severity: "low" | "medium" | "high" | "critical";
  type: string;
  source: string;
  description: string;
  status: "active" | "resolved" | "mitigated";
  action_taken?: string;
}

export default function ImmuneEventsPage() {
  const [events, setEvents] = useState<ThreatEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, active: 0, resolved: 0 });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, []);

  async function fetchEvents() {
    try {
      const data = await getJSON<ThreatEvent[]>("/api/threats/events");
      if (!Array.isArray(data)) {
        throw new Error("Invalid threat event response");
      }
      setEvents(data);
      setStats({
        total: data.length,
        active: data.filter((e) => e.status === "active").length,
        resolved: data.filter((e) => e.status === "resolved").length,
      });
      setError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to fetch immune events";
      setError(message);
      setEvents([]);
      setStats({ total: 0, active: 0, resolved: 0 });
    } finally {
      setLoading(false);
    }
  }

  const activeEvents = events.filter((e) => e.status === "active");
  const resolvedEvents = events.filter((e) => e.status !== "active");

  if (loading) return <PageSkeleton />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Immune System Events</h1>
          <p className="text-sm text-muted-foreground">
            Threat detection and security events
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchEvents}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-red-500/30 bg-red-500/10">
          <CardContent className="pt-4 text-sm text-red-200">
            Failed to load immune events: {error}
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Events</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Shield className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Threats</p>
                <p className="text-2xl font-bold">{stats.active}</p>
              </div>
              <ShieldAlert className="h-8 w-8 text-amber-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Resolved</p>
                <p className="text-2xl font-bold">{stats.resolved}</p>
              </div>
              <ShieldCheck className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="active" className="w-full">
        <TabsList>
          <TabsTrigger value="active">
            Active Threats ({activeEvents.length})
          </TabsTrigger>
          <TabsTrigger value="resolved">
            Resolved ({resolvedEvents.length})
          </TabsTrigger>
          <TabsTrigger value="all">All Events ({events.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4">
          <EventsList events={activeEvents} />
        </TabsContent>
        <TabsContent value="resolved" className="mt-4">
          <EventsList events={resolvedEvents} />
        </TabsContent>
        <TabsContent value="all" className="mt-4">
          <EventsList events={events} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function EventsList({ events }: { events: ThreatEvent[] }) {
  if (events.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          <ShieldCheck className="h-12 w-12 mx-auto mb-4 text-green-500" />
          <p>No threat events found</p>
          <p className="text-sm">System is secure</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="divide-y">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-4 p-4 hover:bg-secondary/50 transition-colors"
            >
              <SeverityIcon severity={event.severity} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{event.description}</span>
                  <SeverityBadge severity={event.severity} />
                  <StatusBadge status={event.status} />
                </div>
                <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(event.timestamp).toLocaleString()}
                  </span>
                  <span>Source: {event.source}</span>
                  <span>Type: {event.type}</span>
                </div>
                {event.action_taken && (
                  <div className="mt-2 text-sm">
                    <span className="text-muted-foreground">Action: </span>
                    <span className="text-green-600">{event.action_taken}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SeverityIcon({ severity }: { severity: string }) {
  const icons = {
    low: <Shield className="h-5 w-5 text-blue-500" />,
    medium: <AlertTriangle className="h-5 w-5 text-amber-500" />,
    high: <ShieldAlert className="h-5 w-5 text-orange-500" />,
    critical: <ShieldAlert className="h-5 w-5 text-red-500" />,
  };
  return icons[severity as keyof typeof icons] || icons.low;
}

function SeverityBadge({ severity }: { severity: string }) {
  const variants: Record<string, string> = {
    low: "bg-blue-500/10 text-blue-500",
    medium: "bg-amber-500/10 text-amber-500",
    high: "bg-orange-500/10 text-orange-500",
    critical: "bg-red-500/10 text-red-500",
  };
  return (
    <Badge variant="outline" className={variants[severity] || variants.low}>
      {severity}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    active: "bg-red-500/10 text-red-500",
    mitigated: "bg-amber-500/10 text-amber-500",
    resolved: "bg-green-500/10 text-green-500",
  };
  return (
    <Badge variant="outline" className={variants[status] || variants.active}>
      {status}
    </Badge>
  );
}

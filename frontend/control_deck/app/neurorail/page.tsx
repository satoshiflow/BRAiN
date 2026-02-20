"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


/**
 * NeuroRail Dashboard Overview (Phase 3 Frontend)
 *
 * Main dashboard for NeuroRail system with links to all monitors.
 */


import React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useSSEContext } from '@/components/neurorail/sse-provider';
import {
  Activity,
  GitBranch,
  Zap,
  DollarSign,
  BarChart3,
  ArrowRight,
  Wifi,
  WifiOff,
} from 'lucide-react';

export default function NeuroRailDashboard() {
  const { isConnected, events } = useSSEContext();

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">NeuroRail</h1>
          <p className="text-muted-foreground">
            Real-time execution governance and observability
          </p>
        </div>
        <Badge variant={isConnected ? 'default' : 'destructive'} className="flex items-center gap-2">
          {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {isConnected ? 'Connected' : 'Disconnected'}
        </Badge>
      </div>

      {/* Event Stream Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Event Stream</CardTitle>
          <CardDescription>Server-Sent Events subscription status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Connection Status</p>
              <p className="text-2xl font-bold">{isConnected ? 'Active' : 'Inactive'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Events</p>
              <p className="text-2xl font-bold">{events.length}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Channels</p>
              <p className="text-2xl font-bold">7</p>
              <p className="text-xs text-muted-foreground">
                audit, lifecycle, metrics, reflex, governor, enforcement, all
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Monitor Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MonitorCard
          title="Trace Explorer"
          description="Complete trace chain visualization from mission to resource"
          icon={GitBranch}
          href="/neurorail/trace"
          color="bg-blue-500"
        />

        <MonitorCard
          title="Reflex Monitor"
          description="Circuit breakers, triggers, and automated reflex actions"
          icon={Zap}
          href="/neurorail/reflex"
          color="bg-yellow-500"
        />

        <MonitorCard
          title="Budget Dashboard"
          description="Enforcement metrics: timeouts, retries, parallelism, cost"
          icon={DollarSign}
          href="/neurorail/budget"
          color="bg-green-500"
        />

        <MonitorCard
          title="Lifecycle Monitor"
          description="Job lifecycle states and transitions in real-time"
          icon={Activity}
          href="/neurorail/lifecycle"
          color="bg-purple-500"
        />

        <MonitorCard
          title="Metrics Dashboard"
          description="Prometheus metrics and telemetry snapshots"
          icon={BarChart3}
          href="/neurorail/metrics"
          color="bg-orange-500"
        />

        <MonitorCard
          title="Governor Panel"
          description="Mode decisions and manifest governance"
          icon={Activity}
          href="/neurorail/governor"
          color="bg-indigo-500"
        />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <QuickStatCard title="Audit Events" value={events.filter(e => e.channel === 'audit').length} />
        <QuickStatCard title="Lifecycle Events" value={events.filter(e => e.channel === 'lifecycle').length} />
        <QuickStatCard title="Reflex Events" value={events.filter(e => e.channel === 'reflex').length} />
        <QuickStatCard title="Enforcement Events" value={events.filter(e => e.channel === 'enforcement').length} />
      </div>
    </div>
  );
}

function MonitorCard({
  title,
  description,
  icon: Icon,
  href,
  color,
}: {
  title: string;
  description: string;
  icon: any;
  href: string;
  color: string;
}) {
  return (
    <Link href={href}>
      <Card className="cursor-pointer hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className={`${color} p-3 rounded-full`}>
              <Icon className="h-6 w-6 text-white" />
            </div>
            <ArrowRight className="h-5 w-5 text-muted-foreground" />
          </div>
          <CardTitle className="mt-4">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </Link>
  );
}

function QuickStatCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

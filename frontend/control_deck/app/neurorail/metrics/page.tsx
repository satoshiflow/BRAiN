"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

/**
 * Metrics Dashboard Page
 *
 * Prometheus metrics visualization for NeuroRail telemetry
 */


import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Loader2, TrendingUp, TrendingDown, Activity, Clock, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface MetricsSnapshot {
  timestamp: string;
  entity_counts: {
    missions: number;
    plans: number;
    jobs: number;
    attempts: number;
  };
  active_executions: {
    running_attempts: number;
    queued_jobs: number;
  };
  error_rates: {
    mechanical_errors: number;
    ethical_errors: number;
  };
  prometheus_metrics: {
    neurorail_attempts_total: number;
    neurorail_active_missions: number;
    neurorail_tt_first_signal_ms_avg: number;
    [key: string]: number;
  };
}

async function fetchMetricsSnapshot(): Promise<MetricsSnapshot> {
  const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE ?? 'http://localhost:8000';
  const response = await fetch(`${API_BASE}/api/neurorail/v1/telemetry/snapshot`);
  if (!response.ok) {
    throw new Error(`Failed to fetch metrics: ${response.statusText}`);
  }
  return response.json();
}

export default function MetricsPage() {
  const { data: snapshot, isLoading, error, isError } = useQuery<MetricsSnapshot>({
    queryKey: ['neurorail', 'metrics', 'snapshot'],
    queryFn: fetchMetricsSnapshot,
    refetchInterval: 10_000, // Refresh every 10 seconds
    staleTime: 5_000,
    retry: 2,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Metrics Dashboard</h1>
          <p className="text-muted-foreground">
            Prometheus metrics and telemetry for NeuroRail execution governance
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load metrics: {error?.message || 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const entityData = snapshot ? [
    { name: 'Missions', count: snapshot.entity_counts.missions, color: '#3b82f6' },
    { name: 'Plans', count: snapshot.entity_counts.plans, color: '#8b5cf6' },
    { name: 'Jobs', count: snapshot.entity_counts.jobs, color: '#10b981' },
    { name: 'Attempts', count: snapshot.entity_counts.attempts, color: '#f59e0b' },
  ] : [];

  const errorData = snapshot ? [
    { name: 'Mechanical', rate: (snapshot.error_rates.mechanical_errors * 100).toFixed(2), color: '#f59e0b' },
    { name: 'Ethical', rate: (snapshot.error_rates.ethical_errors * 100).toFixed(2), color: '#ef4444' },
  ] : [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Metrics Dashboard</h1>
        <p className="text-muted-foreground">
          Prometheus metrics and telemetry for NeuroRail execution governance
        </p>
      </div>

      {/* Real-time Snapshot */}
      {snapshot && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Active Missions */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Missions</CardTitle>
              <Activity className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{snapshot.prometheus_metrics.neurorail_active_missions || 0}</div>
              <p className="text-xs text-muted-foreground">
                {snapshot.entity_counts.missions} total missions
              </p>
            </CardContent>
          </Card>

          {/* Running Attempts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Running Attempts</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{snapshot.active_executions.running_attempts}</div>
              <p className="text-xs text-muted-foreground">
                {snapshot.active_executions.queued_jobs} queued jobs
              </p>
            </CardContent>
          </Card>

          {/* Total Attempts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Attempts</CardTitle>
              <Activity className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{snapshot.prometheus_metrics.neurorail_attempts_total || 0}</div>
              <p className="text-xs text-muted-foreground">
                All-time attempt count
              </p>
            </CardContent>
          </Card>

          {/* Avg TTFS */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg TTFS</CardTitle>
              <Clock className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {snapshot.prometheus_metrics.neurorail_tt_first_signal_ms_avg?.toFixed(1) || 0}ms
              </div>
              <p className="text-xs text-muted-foreground">
                Time to first signal
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Entity Counts Chart */}
      {snapshot && (
        <Card>
          <CardHeader>
            <CardTitle>Entity Counts</CardTitle>
            <CardDescription>
              Total count of missions, plans, jobs, and attempts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={entityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Error Rates */}
      {snapshot && (
        <Card>
          <CardHeader>
            <CardTitle>Error Rates</CardTitle>
            <CardDescription>
              Mechanical vs. ethical error rates (percentage)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="text-sm font-medium">Mechanical Errors</p>
                    <p className="text-xs text-muted-foreground">Retriable system errors</p>
                  </div>
                  <Badge variant={snapshot.error_rates.mechanical_errors > 0.05 ? "destructive" : "secondary"}>
                    {(snapshot.error_rates.mechanical_errors * 100).toFixed(2)}%
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="text-sm font-medium">Ethical Errors</p>
                    <p className="text-xs text-muted-foreground">Policy/safety violations</p>
                  </div>
                  <Badge variant={snapshot.error_rates.ethical_errors > 0 ? "destructive" : "secondary"}>
                    {(snapshot.error_rates.ethical_errors * 100).toFixed(2)}%
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Executions */}
      {snapshot && (
        <Card>
          <CardHeader>
            <CardTitle>Active Executions</CardTitle>
            <CardDescription>
              Real-time execution state snapshot
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <div>
                    <p className="text-sm font-medium">Running Attempts</p>
                    <p className="text-xs text-muted-foreground">Currently executing</p>
                  </div>
                </div>
                <div className="text-2xl font-bold">{snapshot.active_executions.running_attempts}</div>
              </div>
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-500" />
                  <div>
                    <p className="text-sm font-medium">Queued Jobs</p>
                    <p className="text-xs text-muted-foreground">Waiting to execute</p>
                  </div>
                </div>
                <div className="text-2xl font-bold">{snapshot.active_executions.queued_jobs}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prometheus Metrics Reference */}
      <Card>
        <CardHeader>
          <CardTitle>Prometheus Metrics Reference</CardTitle>
          <CardDescription>
            Available metrics for external monitoring (Grafana, Prometheus)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2 font-mono">
              <div className="font-semibold">Counters:</div>
              <div></div>
              <div className="pl-4">neurorail_attempts_total</div>
              <div className="text-muted-foreground">Total attempts by entity type and status</div>
              <div className="pl-4">neurorail_attempts_failed_total</div>
              <div className="text-muted-foreground">Failed attempts by error category/code</div>
              <div className="pl-4">neurorail_budget_violations_total</div>
              <div className="text-muted-foreground">Budget violations by type</div>
              <div className="pl-4">neurorail_reflex_actions_total</div>
              <div className="text-muted-foreground">Reflex actions by type</div>
            </div>
            <div className="grid grid-cols-2 gap-2 font-mono mt-4">
              <div className="font-semibold">Gauges:</div>
              <div></div>
              <div className="pl-4">neurorail_active_missions</div>
              <div className="text-muted-foreground">Currently active missions</div>
              <div className="pl-4">neurorail_active_jobs</div>
              <div className="text-muted-foreground">Currently active jobs</div>
              <div className="pl-4">neurorail_active_attempts</div>
              <div className="text-muted-foreground">Currently active attempts</div>
              <div className="pl-4">neurorail_resources_by_state</div>
              <div className="text-muted-foreground">Resources by type and state</div>
            </div>
            <div className="grid grid-cols-2 gap-2 font-mono mt-4">
              <div className="font-semibold">Histograms:</div>
              <div></div>
              <div className="pl-4">neurorail_attempt_duration_ms</div>
              <div className="text-muted-foreground">Attempt execution time distribution</div>
              <div className="pl-4">neurorail_job_duration_ms</div>
              <div className="text-muted-foreground">Job execution time distribution</div>
              <div className="pl-4">neurorail_mission_duration_ms</div>
              <div className="text-muted-foreground">Mission execution time distribution</div>
              <div className="pl-4">neurorail_tt_first_signal_ms</div>
              <div className="text-muted-foreground">Time to first signal (TTFS)</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Last Update Timestamp */}
      {snapshot && (
        <div className="text-xs text-muted-foreground text-right">
          Last updated: {new Date(snapshot.timestamp).toLocaleString()}
        </div>
      )}
    </div>
  );
}

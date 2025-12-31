/**
 * Budget Dashboard (Phase 3 Frontend - SPRINT 6)
 *
 * Visualizes budget enforcement metrics:
 * - Timeout enforcement
 * - Retry attempts
 * - Parallelism limits
 * - Cost tracking (LLM tokens, API calls, credits)
 *
 * @example
 * ```tsx
 * <BudgetDashboard />
 * ```
 */

"use client";

import React, { useState, useEffect } from 'react';
import { useFilteredSSE } from '@/components/neurorail/sse-provider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Clock, Repeat, Users, DollarSign, AlertTriangle, CheckCircle } from 'lucide-react';

export function BudgetDashboard() {
  // Subscribe to enforcement events
  const enforcementEvents = useFilteredSSE({
    channels: ['enforcement'],
  });

  // Aggregate budget metrics
  const [timeoutStats, setTimeoutStats] = useState({ total: 0, grace_periods: 0 });
  const [retryStats, setRetryStats] = useState({ total: 0, successful: 0 });
  const [parallelismStats, setParallelismStats] = useState({ total: 0, rejected: 0 });
  const [costStats, setCostStats] = useState({
    llm_tokens: 0,
    api_calls: 0,
    cost_credits: 0,
    violations: 0,
  });

  // Time series data (last 20 events)
  const [timeoutTimeSeries, setTimeoutTimeSeries] = useState<any[]>([]);
  const [retryTimeSeries, setRetryTimeSeries] = useState<any[]>([]);
  const [costTimeSeries, setCostTimeSeries] = useState<any[]>([]);

  // Process enforcement events
  useEffect(() => {
    enforcementEvents.forEach((event) => {
      const timestamp = new Date(event.timestamp * 1000).toLocaleTimeString();

      if (event.event_type === 'timeout_enforced') {
        setTimeoutStats((prev) => ({
          total: prev.total + 1,
          grace_periods: prev.grace_periods + (event.data.grace_period_invoked ? 1 : 0),
        }));
        setTimeoutTimeSeries((prev) => [
          ...prev.slice(-19),
          { time: timestamp, timeouts: prev.length + 1 },
        ]);
      }

      if (event.event_type === 'retry_attempted') {
        setRetryStats((prev) => ({
          total: prev.total + 1,
          successful: prev.successful + (event.data.success ? 1 : 0),
        }));
        setRetryTimeSeries((prev) => [
          ...prev.slice(-19),
          { time: timestamp, retries: prev.length + 1 },
        ]);
      }

      if (event.event_type === 'parallelism_rejected') {
        setParallelismStats((prev) => ({
          total: prev.total + 1,
          rejected: prev.rejected + 1,
        }));
      }

      if (event.event_type === 'cost_tracked') {
        setCostStats((prev) => ({
          llm_tokens: prev.llm_tokens + (event.data.llm_tokens || 0),
          api_calls: prev.api_calls + 1,
          cost_credits: prev.cost_credits + (event.data.cost || 0),
          violations: prev.violations,
        }));
        setCostTimeSeries((prev) => [
          ...prev.slice(-19),
          {
            time: timestamp,
            tokens: prev.llm_tokens + (event.data.llm_tokens || 0),
            cost: prev.cost_credits + (event.data.cost || 0),
          },
        ]);
      }

      if (event.event_type === 'budget_violation') {
        setCostStats((prev) => ({
          ...prev,
          violations: prev.violations + 1,
        }));
      }
    });
  }, [enforcementEvents]);

  // Calculate rates
  const timeoutRate = timeoutStats.total > 0 ? (timeoutStats.grace_periods / timeoutStats.total) * 100 : 0;
  const retrySuccessRate = retryStats.total > 0 ? (retryStats.successful / retryStats.total) * 100 : 0;
  const parallelismRejectionRate =
    parallelismStats.total > 0 ? (parallelismStats.rejected / parallelismStats.total) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <BudgetStatCard
          title="Timeouts"
          value={timeoutStats.total}
          subtitle={`${timeoutStats.grace_periods} grace periods`}
          icon={Clock}
          color="bg-blue-500"
        />
        <BudgetStatCard
          title="Retries"
          value={retryStats.total}
          subtitle={`${retrySuccessRate.toFixed(0)}% success rate`}
          icon={Repeat}
          color="bg-green-500"
        />
        <BudgetStatCard
          title="Parallelism"
          value={parallelismStats.total}
          subtitle={`${parallelismStats.rejected} rejected`}
          icon={Users}
          color="bg-yellow-500"
        />
        <BudgetStatCard
          title="Cost"
          value={costStats.cost_credits.toFixed(2)}
          subtitle={`${costStats.llm_tokens} tokens`}
          icon={DollarSign}
          color="bg-purple-500"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeout Time Series */}
        <Card>
          <CardHeader>
            <CardTitle>Timeout Enforcement</CardTitle>
            <CardDescription>Timeout events over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={timeoutTimeSeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="timeouts" stroke="#3b82f6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Retry Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Retry Distribution</CardTitle>
            <CardDescription>Retry attempts over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={retryTimeSeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="retries" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Tracking */}
        <Card>
          <CardHeader>
            <CardTitle>Cost Tracking</CardTitle>
            <CardDescription>LLM tokens and cost over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={costTimeSeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="tokens" stroke="#8b5cf6" strokeWidth={2} />
                <Line yAxisId="right" type="monotone" dataKey="cost" stroke="#f59e0b" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Budget Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Budget Breakdown</CardTitle>
            <CardDescription>Enforcement metrics summary</CardDescription>
          </CardHeader>
          <CardContent>
            <BudgetBreakdownPieChart
              data={[
                { name: 'Timeouts', value: timeoutStats.total, color: '#3b82f6' },
                { name: 'Retries', value: retryStats.total, color: '#10b981' },
                { name: 'Parallelism', value: parallelismStats.total, color: '#f59e0b' },
                { name: 'Violations', value: costStats.violations, color: '#ef4444' },
              ]}
            />
          </CardContent>
        </Card>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Timeout Details */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Timeout Enforcement</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricRow label="Total Timeouts" value={timeoutStats.total} />
            <MetricRow label="Grace Periods" value={timeoutStats.grace_periods} />
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Grace Period Rate</span>
                <span className="font-medium">{timeoutRate.toFixed(1)}%</span>
              </div>
              <Progress value={timeoutRate} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Retry Details */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Retry Enforcement</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricRow label="Total Retries" value={retryStats.total} />
            <MetricRow label="Successful" value={retryStats.successful} />
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Success Rate</span>
                <span className="font-medium">{retrySuccessRate.toFixed(1)}%</span>
              </div>
              <Progress value={retrySuccessRate} className="h-2" />
            </div>
          </CardContent>
        </Card>

        {/* Cost Details */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cost Tracking</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricRow label="LLM Tokens" value={costStats.llm_tokens.toLocaleString()} />
            <MetricRow label="API Calls" value={costStats.api_calls} />
            <MetricRow label="Cost Credits" value={costStats.cost_credits.toFixed(2)} />
            <MetricRow label="Violations" value={costStats.violations} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// Components
// ============================================================================

function BudgetStatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
}: {
  title: string;
  value: number | string;
  subtitle: string;
  icon: any;
  color: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className={`${color} p-2 rounded-full`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function BudgetBreakdownPieChart({ data }: { data: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={(entry) => `${entry.name}: ${entry.value}`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

function MetricRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

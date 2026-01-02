/**
 * Lifecycle Monitor (Phase 3 Frontend - SPRINT 6)
 *
 * Real-time visualization of job lifecycle states:
 * - State flow diagram
 * - Active jobs by state
 * - Transition history
 * - Cooldown periods
 *
 * @example
 * ```tsx
 * <LifecycleMonitor />
 * ```
 */

"use client";

import React, { useState, useEffect } from 'react';
import { useFilteredSSE } from '@/components/neurorail/sse-provider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  Clock,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';

interface JobState {
  job_id: string;
  state: string;
  last_updated: number;
  cooldown_until?: number;
}

export function LifecycleMonitor() {
  // Subscribe to lifecycle events
  const lifecycleEvents = useFilteredSSE({
    channels: ['lifecycle'],
  });

  // Track active jobs
  const [activeJobs, setActiveJobs] = useState<Map<string, JobState>>(new Map());

  // Track state counts
  const [stateCounts, setStateCounts] = useState<Record<string, number>>({
    pending: 0,
    running: 0,
    suspended: 0,
    throttled: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
  });

  // Track recent transitions
  const [recentTransitions, setRecentTransitions] = useState<any[]>([]);

  // Process lifecycle events
  useEffect(() => {
    lifecycleEvents.forEach((event) => {
      if (event.event_type === 'state_transition') {
        const { entity_id, to_state, from_state, cooldown_until } = event.data;

        // Update active jobs
        setActiveJobs((prev) => {
          const next = new Map(prev);
          next.set(entity_id, {
            job_id: entity_id,
            state: to_state,
            last_updated: event.timestamp,
            cooldown_until,
          });
          return next;
        });

        // Track recent transitions
        setRecentTransitions((prev) => [
          {
            job_id: entity_id,
            from_state,
            to_state,
            timestamp: event.timestamp,
          },
          ...prev.slice(0, 19), // Keep last 20
        ]);
      }
    });
  }, [lifecycleEvents]);

  // Recalculate state counts
  useEffect(() => {
    const counts: Record<string, number> = {
      pending: 0,
      running: 0,
      suspended: 0,
      throttled: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    };

    activeJobs.forEach((job) => {
      counts[job.state] = (counts[job.state] || 0) + 1;
    });

    setStateCounts(counts);
  }, [activeJobs]);

  return (
    <div className="space-y-6">
      {/* State Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <StateCard state="pending" count={stateCounts.pending} color="bg-gray-500" icon={Clock} />
        <StateCard state="running" count={stateCounts.running} color="bg-blue-500" icon={Play} />
        <StateCard state="suspended" count={stateCounts.suspended} color="bg-yellow-500" icon={Pause} />
        <StateCard state="throttled" count={stateCounts.throttled} color="bg-orange-500" icon={Clock} />
        <StateCard state="completed" count={stateCounts.completed} color="bg-green-500" icon={CheckCircle} />
        <StateCard state="failed" count={stateCounts.failed} color="bg-red-500" icon={XCircle} />
        <StateCard state="cancelled" count={stateCounts.cancelled} color="bg-gray-600" icon={XCircle} />
      </div>

      {/* State Flow Diagram */}
      <Card>
        <CardHeader>
          <CardTitle>Lifecycle State Flow</CardTitle>
          <CardDescription>Valid state transitions</CardDescription>
        </CardHeader>
        <CardContent>
          <StateFlowDiagram />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Jobs */}
        <Card>
          <CardHeader>
            <CardTitle>Active Jobs</CardTitle>
            <CardDescription>{activeJobs.size} jobs tracked</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              {activeJobs.size === 0 ? (
                <p className="text-sm text-muted-foreground">No active jobs</p>
              ) : (
                <div className="space-y-3">
                  {Array.from(activeJobs.values())
                    .sort((a, b) => b.last_updated - a.last_updated)
                    .map((job) => (
                      <ActiveJobCard key={job.job_id} job={job} />
                    ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Recent Transitions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Transitions</CardTitle>
            <CardDescription>Last 20 state changes</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              {recentTransitions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No transitions</p>
              ) : (
                <div className="space-y-3">
                  {recentTransitions.map((transition, idx) => (
                    <TransitionCard key={idx} transition={transition} />
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// Components
// ============================================================================

function StateCard({
  state,
  count,
  color,
  icon: Icon,
}: {
  state: string;
  count: number;
  color: string;
  icon: any;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className={`${color} p-2 rounded-full`}>
            <Icon className="h-3 w-3 text-white" />
          </div>
          <CardTitle className="text-xs uppercase">{state}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{count}</div>
      </CardContent>
    </Card>
  );
}

function StateFlowDiagram() {
  const states = [
    { state: 'PENDING', next: ['RUNNING', 'CANCELLED'] },
    { state: 'RUNNING', next: ['SUSPENDED', 'THROTTLED', 'COMPLETED', 'FAILED', 'CANCELLED'] },
    { state: 'SUSPENDED', next: ['RUNNING', 'CANCELLED'] },
    { state: 'THROTTLED', next: ['RUNNING', 'SUSPENDED', 'CANCELLED'] },
    { state: 'COMPLETED', next: [] },
    { state: 'FAILED', next: [] },
    { state: 'CANCELLED', next: [] },
  ];

  return (
    <div className="space-y-4">
      {states.map((s) => (
        <div key={s.state} className="flex items-center gap-3 text-sm">
          <Badge className="min-w-[100px] justify-center">{s.state}</Badge>
          {s.next.length > 0 ? (
            <>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
              <div className="flex flex-wrap gap-2">
                {s.next.map((next) => (
                  <Badge key={next} variant="outline">
                    {next}
                  </Badge>
                ))}
              </div>
            </>
          ) : (
            <span className="text-xs text-muted-foreground">(Terminal State)</span>
          )}
        </div>
      ))}
    </div>
  );
}

function ActiveJobCard({ job }: { job: JobState }) {
  const stateColors = {
    pending: 'bg-gray-500',
    running: 'bg-blue-500',
    suspended: 'bg-yellow-500',
    throttled: 'bg-orange-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-600',
  };

  const colorClass = stateColors[job.state as keyof typeof stateColors] || 'bg-gray-500';

  // Check if job is in cooldown
  const now = Date.now() / 1000;
  const inCooldown = job.cooldown_until && job.cooldown_until > now;
  const cooldownRemaining = inCooldown ? Math.ceil((job.cooldown_until! - now)) : 0;

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-mono text-muted-foreground">{job.job_id}</p>
        <Badge className={colorClass}>{job.state.toUpperCase()}</Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        Updated {new Date(job.last_updated * 1000).toLocaleTimeString()}
      </p>
      {inCooldown && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Cooldown</span>
            <span className="font-medium">{cooldownRemaining}s remaining</span>
          </div>
          <Progress value={(cooldownRemaining / 60) * 100} className="h-1" />
        </div>
      )}
    </div>
  );
}

function TransitionCard({ transition }: { transition: any }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <Badge variant="outline" className="min-w-[80px] justify-center">
        {transition.from_state || 'INIT'}
      </Badge>
      <ArrowRight className="h-4 w-4 text-muted-foreground" />
      <Badge className="min-w-[80px] justify-center">{transition.to_state}</Badge>
      <span className="text-xs text-muted-foreground font-mono ml-auto">
        {new Date(transition.timestamp * 1000).toLocaleTimeString()}
      </span>
    </div>
  );
}

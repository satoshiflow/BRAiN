/**
 * Reflex Monitor Dashboard (Phase 3 Frontend)
 *
 * Real-time monitoring of reflex system:
 * - Circuit breaker states
 * - Reflex triggers
 * - Reflex actions
 * - Lifecycle state transitions
 *
 * @example
 * ```tsx
 * <ReflexMonitor />
 * ```
 */

"use client";

import React, { useState, useEffect } from 'react';
import { useFilteredSSE, useLatestSSEEvent } from '@/components/neurorail/sse-provider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
  Pause,
  Play,
  XCircle,
} from 'lucide-react';

export function ReflexMonitor() {
  // Subscribe to reflex events
  const reflexEvents = useFilteredSSE({
    channels: ['reflex'],
  });

  const lifecycleEvents = useFilteredSSE({
    channels: ['lifecycle'],
    eventTypes: ['state_transition'],
  });

  // Track circuit breaker states
  const [circuitBreakers, setCircuitBreakers] = useState<Map<string, CircuitBreakerState>>(
    new Map()
  );

  // Track trigger activations
  const [triggerActivations, setTriggerActivations] = useState<TriggerActivation[]>([]);

  // Track reflex actions
  const [reflexActions, setReflexActions] = useState<ReflexActionRecord[]>([]);

  // Process reflex events
  useEffect(() => {
    reflexEvents.forEach((event) => {
      if (event.event_type === 'circuit_state_changed') {
        setCircuitBreakers((prev) => {
          const next = new Map(prev);
          next.set(event.data.circuit_id, {
            circuit_id: event.data.circuit_id,
            state: event.data.to_state,
            failure_count: event.data.failure_count || 0,
            success_count: event.data.success_count || 0,
            last_updated: event.timestamp,
          });
          return next;
        });
      }

      if (event.event_type === 'trigger_activated') {
        setTriggerActivations((prev) => [
          {
            trigger_id: event.data.trigger_id,
            reason: event.data.reason,
            error_rate: event.data.error_rate,
            timestamp: event.timestamp,
          },
          ...prev.slice(0, 19), // Keep last 20
        ]);
      }

      if (event.event_type === 'reflex_action_executed') {
        setReflexActions((prev) => [
          {
            job_id: event.data.job_id,
            action_type: event.data.action_type,
            reason: event.data.reason,
            success: event.data.success,
            timestamp: event.timestamp,
          },
          ...prev.slice(0, 19), // Keep last 20
        ]);
      }
    });
  }, [reflexEvents]);

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Circuit Breakers"
          value={circuitBreakers.size}
          subtitle={`${Array.from(circuitBreakers.values()).filter((cb) => cb.state === 'open').length} open`}
          icon={Activity}
        />
        <StatCard
          title="Trigger Activations"
          value={triggerActivations.length}
          subtitle="Last 20 events"
          icon={Zap}
        />
        <StatCard
          title="Reflex Actions"
          value={reflexActions.length}
          subtitle="Last 20 actions"
          icon={AlertTriangle}
        />
        <StatCard
          title="Active Suspensions"
          value={reflexActions.filter((a) => a.action_type === 'suspend').length}
          subtitle="Jobs suspended"
          icon={Pause}
        />
      </div>

      {/* Circuit Breakers */}
      <Card>
        <CardHeader>
          <CardTitle>Circuit Breakers</CardTitle>
          <CardDescription>Real-time circuit breaker states</CardDescription>
        </CardHeader>
        <CardContent>
          {circuitBreakers.size === 0 ? (
            <p className="text-sm text-muted-foreground">No circuit breakers active</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from(circuitBreakers.values()).map((cb) => (
                <CircuitBreakerCard key={cb.circuit_id} circuitBreaker={cb} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trigger Activations */}
        <Card>
          <CardHeader>
            <CardTitle>Trigger Activations</CardTitle>
            <CardDescription>Error rate and budget violation triggers</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              {triggerActivations.length === 0 ? (
                <p className="text-sm text-muted-foreground">No trigger activations</p>
              ) : (
                <div className="space-y-3">
                  {triggerActivations.map((trigger, idx) => (
                    <TriggerActivationCard key={idx} trigger={trigger} />
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Reflex Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Reflex Actions</CardTitle>
            <CardDescription>Automated reflex responses</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              {reflexActions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No reflex actions</p>
              ) : (
                <div className="space-y-3">
                  {reflexActions.map((action, idx) => (
                    <ReflexActionCard key={idx} action={action} />
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Lifecycle State Stream */}
      <Card>
        <CardHeader>
          <CardTitle>Lifecycle State Stream</CardTitle>
          <CardDescription>Real-time job state transitions</CardDescription>
        </CardHeader>
        <CardContent>
          <LifecycleStateStream events={lifecycleEvents} />
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// Types
// ============================================================================

interface CircuitBreakerState {
  circuit_id: string;
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  success_count: number;
  last_updated: number;
}

interface TriggerActivation {
  trigger_id: string;
  reason: string;
  error_rate?: number;
  timestamp: number;
}

interface ReflexActionRecord {
  job_id: string;
  action_type: 'suspend' | 'throttle' | 'alert' | 'cancel';
  reason: string;
  success: boolean;
  timestamp: number;
}

// ============================================================================
// Components
// ============================================================================

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: number;
  subtitle: string;
  icon: any;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function CircuitBreakerCard({ circuitBreaker }: { circuitBreaker: CircuitBreakerState }) {
  const stateColors = {
    closed: 'bg-green-500',
    open: 'bg-red-500',
    half_open: 'bg-yellow-500',
  };

  const stateIcons = {
    closed: CheckCircle2,
    open: XCircle,
    half_open: Clock,
  };

  const Icon = stateIcons[circuitBreaker.state];
  const colorClass = stateColors[circuitBreaker.state];

  const totalCalls = circuitBreaker.failure_count + circuitBreaker.success_count;
  const failureRate = totalCalls > 0 ? (circuitBreaker.failure_count / totalCalls) * 100 : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono">{circuitBreaker.circuit_id}</CardTitle>
          <Badge className={colorClass}>{circuitBreaker.state.toUpperCase()}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Failure Rate</span>
            <span className="font-medium">{failureRate.toFixed(1)}%</span>
          </div>
          <Progress value={failureRate} className="h-2" />
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Failures:</span>
          <span className="font-mono">{circuitBreaker.failure_count}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Successes:</span>
          <span className="font-mono">{circuitBreaker.success_count}</span>
        </div>
        <div className="text-xs text-muted-foreground">
          Updated {new Date(circuitBreaker.last_updated * 1000).toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>
  );
}

function TriggerActivationCard({ trigger }: { trigger: TriggerActivation }) {
  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium font-mono">{trigger.trigger_id}</p>
        <Badge variant="destructive">ACTIVATED</Badge>
      </div>
      <p className="text-sm text-muted-foreground">{trigger.reason}</p>
      {trigger.error_rate !== undefined && (
        <p className="text-xs text-muted-foreground">Error Rate: {(trigger.error_rate * 100).toFixed(1)}%</p>
      )}
      <p className="text-xs text-muted-foreground">
        {new Date(trigger.timestamp * 1000).toLocaleString()}
      </p>
    </div>
  );
}

function ReflexActionCard({ action }: { action: ReflexActionRecord }) {
  const actionIcons = {
    suspend: Pause,
    throttle: Clock,
    alert: AlertTriangle,
    cancel: XCircle,
  };

  const actionColors = {
    suspend: 'bg-yellow-500',
    throttle: 'bg-blue-500',
    alert: 'bg-orange-500',
    cancel: 'bg-red-500',
  };

  const Icon = actionIcons[action.action_type];
  const colorClass = actionColors[action.action_type];

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 ${colorClass} rounded-full`} />
        <p className="text-sm font-medium">{action.action_type.toUpperCase()}</p>
        <Badge variant={action.success ? 'outline' : 'destructive'}>
          {action.success ? 'SUCCESS' : 'FAILED'}
        </Badge>
      </div>
      <p className="text-xs font-mono text-muted-foreground">{action.job_id}</p>
      <p className="text-sm text-muted-foreground">{action.reason}</p>
      <p className="text-xs text-muted-foreground">
        {new Date(action.timestamp * 1000).toLocaleString()}
      </p>
    </div>
  );
}

function LifecycleStateStream({ events }: { events: any[] }) {
  const latestEvents = events.slice(0, 10);

  if (latestEvents.length === 0) {
    return <p className="text-sm text-muted-foreground">No lifecycle events</p>;
  }

  return (
    <ScrollArea className="h-[300px]">
      <div className="space-y-2">
        {latestEvents.map((event, idx) => (
          <div key={idx} className="flex items-center gap-3 text-sm">
            <Badge variant="outline">{event.data.from_state || 'INIT'}</Badge>
            <span className="text-muted-foreground">→</span>
            <Badge>{event.data.to_state}</Badge>
            <span className="text-xs text-muted-foreground font-mono ml-auto">
              {event.data.entity_id}
            </span>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}

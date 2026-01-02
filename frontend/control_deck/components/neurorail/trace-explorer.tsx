/**
 * Trace Explorer Component (Phase 3 Frontend - Why-View)
 *
 * Visualizes complete trace chain: mission → plan → job → attempt → resource
 * Shows audit events, lifecycle transitions, and execution metrics.
 *
 * @example
 * ```tsx
 * <TraceExplorer entityType="attempt" entityId="a_123" />
 * ```
 */

"use client";

import React, { useState, useEffect } from 'react';
import { neurorailAPI, type TraceChain, type AuditEvent, type StateTransition } from '@/lib/neurorail-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertCircle, CheckCircle, Clock, ArrowRight, ChevronDown, ChevronRight } from 'lucide-react';

interface TraceExplorerProps {
  entityType: 'mission' | 'plan' | 'job' | 'attempt';
  entityId: string;
}

export function TraceExplorer({ entityType, entityId }: TraceExplorerProps) {
  const [traceChain, setTraceChain] = useState<TraceChain | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [lifecycleHistory, setLifecycleHistory] = useState<StateTransition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch trace chain
  useEffect(() => {
    async function fetchTraceData() {
      setLoading(true);
      setError(null);

      try {
        // Get trace chain
        const chain = await neurorailAPI.identity.getTraceChain(entityType, entityId);
        setTraceChain(chain);

        // Get audit events
        const params: any = {};
        if (chain.mission) params.mission_id = chain.mission.mission_id;
        if (chain.attempt) params.attempt_id = chain.attempt.attempt_id;
        const events = await neurorailAPI.audit.getEvents(params);
        setAuditEvents(events);

        // Get lifecycle history (for job/attempt)
        if (chain.job) {
          const history = await neurorailAPI.lifecycle.getHistory('job', chain.job.job_id);
          setLifecycleHistory(history);
        } else if (chain.attempt) {
          const history = await neurorailAPI.lifecycle.getHistory('attempt', chain.attempt.attempt_id);
          setLifecycleHistory(history);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trace data');
      } finally {
        setLoading(false);
      }
    }

    fetchTraceData();
  }, [entityType, entityId]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trace Explorer</CardTitle>
          <CardDescription>Loading trace chain...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trace Explorer</CardTitle>
          <CardDescription className="text-red-500">{error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!traceChain) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Trace Chain Visualization */}
      <Card>
        <CardHeader>
          <CardTitle>Trace Chain</CardTitle>
          <CardDescription>Complete lineage from mission to resource</CardDescription>
        </CardHeader>
        <CardContent>
          <TraceChainVisualization chain={traceChain} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Audit Events */}
        <Card>
          <CardHeader>
            <CardTitle>Audit Events</CardTitle>
            <CardDescription>{auditEvents.length} events</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              <AuditEventsTimeline events={auditEvents} />
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Lifecycle Transitions */}
        {lifecycleHistory.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Lifecycle Transitions</CardTitle>
              <CardDescription>{lifecycleHistory.length} transitions</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <LifecycleTransitionsView transitions={lifecycleHistory} />
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Trace Chain Visualization
// ============================================================================

function TraceChainVisualization({ chain }: { chain: TraceChain }) {
  return (
    <div className="flex items-center gap-4 flex-wrap">
      {chain.mission && (
        <>
          <TraceEntityCard
            type="Mission"
            id={chain.mission.mission_id}
            timestamp={chain.mission.created_at}
            metadata={chain.mission.tags}
          />
          {chain.plan && <ArrowRight className="text-muted-foreground" />}
        </>
      )}

      {chain.plan && (
        <>
          <TraceEntityCard
            type="Plan"
            id={chain.plan.plan_id}
            timestamp={chain.plan.created_at}
            metadata={{ plan_type: chain.plan.plan_type }}
          />
          {chain.job && <ArrowRight className="text-muted-foreground" />}
        </>
      )}

      {chain.job && (
        <>
          <TraceEntityCard
            type="Job"
            id={chain.job.job_id}
            timestamp={chain.job.created_at}
            metadata={{ job_type: chain.job.job_type }}
          />
          {chain.attempt && <ArrowRight className="text-muted-foreground" />}
        </>
      )}

      {chain.attempt && (
        <TraceEntityCard
          type="Attempt"
          id={chain.attempt.attempt_id}
          timestamp={chain.attempt.created_at}
          metadata={{ attempt_number: chain.attempt.attempt_number.toString() }}
        />
      )}
    </div>
  );
}

function TraceEntityCard({
  type,
  id,
  timestamp,
  metadata,
}: {
  type: string;
  id: string;
  timestamp: string;
  metadata?: Record<string, string>;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border rounded-lg p-4 min-w-[200px] bg-card">
      <div className="flex items-start justify-between">
        <div className="space-y-1 flex-1">
          <p className="text-sm font-medium text-muted-foreground">{type}</p>
          <p className="font-mono text-sm font-semibold">{id}</p>
          <p className="text-xs text-muted-foreground">
            {new Date(timestamp).toLocaleString()}
          </p>
        </div>
        {metadata && Object.keys(metadata).length > 0 && (
          <button onClick={() => setIsExpanded(!isExpanded)} className="ml-2">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {isExpanded && metadata && (
        <div className="mt-3 pt-3 border-t space-y-1">
          {Object.entries(metadata).map(([key, value]) => (
            <div key={key} className="flex justify-between text-xs">
              <span className="text-muted-foreground">{key}:</span>
              <span className="font-mono">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Audit Events Timeline
// ============================================================================

function AuditEventsTimeline({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No audit events</p>;
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <AuditEventItem key={event.audit_id} event={event} />
      ))}
    </div>
  );
}

function AuditEventItem({ event }: { event: AuditEvent }) {
  const severityColors = {
    info: 'bg-blue-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
    debug: 'bg-gray-500',
  };

  const severityIcons = {
    info: CheckCircle,
    warning: AlertCircle,
    error: AlertCircle,
    debug: Clock,
  };

  const Icon = severityIcons[event.severity as keyof typeof severityIcons] || Clock;
  const colorClass = severityColors[event.severity as keyof typeof severityColors] || 'bg-gray-500';

  return (
    <div className="flex gap-3">
      <div className={`w-2 h-2 ${colorClass} rounded-full mt-2`} />
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <p className="text-sm font-medium">{event.event_type}</p>
          <Badge variant="outline" className="text-xs">
            {event.event_category}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{event.message}</p>
        <p className="text-xs text-muted-foreground">
          {new Date(event.timestamp).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// Lifecycle Transitions View
// ============================================================================

function LifecycleTransitionsView({ transitions }: { transitions: StateTransition[] }) {
  if (transitions.length === 0) {
    return <p className="text-sm text-muted-foreground">No lifecycle transitions</p>;
  }

  return (
    <div className="space-y-4">
      {transitions.map((transition) => (
        <div key={transition.transition_id} className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{transition.from_state || 'INIT'}</Badge>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <Badge>{transition.to_state}</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {new Date(transition.timestamp).toLocaleString()}
          </p>
          {transition.metadata && Object.keys(transition.metadata).length > 0 && (
            <div className="text-xs text-muted-foreground font-mono">
              {JSON.stringify(transition.metadata, null, 2)}
            </div>
          )}
          <Separator />
        </div>
      ))}
    </div>
  );
}

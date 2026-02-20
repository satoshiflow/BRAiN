"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


/**
 * Reflex Monitor Page (Phase 3 Frontend)
 *
 * Real-time reflex system monitoring
 */


import React from 'react';
import { ReflexMonitor } from '@/components/neurorail/reflex-monitor';

export default function ReflexMonitorPage() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Reflex Monitor</h1>
        <p className="text-muted-foreground">
          Real-time monitoring of circuit breakers, triggers, and reflex actions
        </p>
      </div>

      {/* Reflex Monitor Component */}
      <ReflexMonitor />
    </div>
  );
}

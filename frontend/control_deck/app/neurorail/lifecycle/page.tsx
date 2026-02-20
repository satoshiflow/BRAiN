"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


/**
 * Lifecycle Monitor Page (Phase 3 Frontend)
 *
 * Job lifecycle state monitoring
 */


import React from 'react';
import { LifecycleMonitor } from '@/components/neurorail/lifecycle-monitor';

export default function LifecycleMonitorPage() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Lifecycle Monitor</h1>
        <p className="text-muted-foreground">
          Real-time job lifecycle states and transitions
        </p>
      </div>

      {/* Lifecycle Monitor Component */}
      <LifecycleMonitor />
    </div>
  );
}

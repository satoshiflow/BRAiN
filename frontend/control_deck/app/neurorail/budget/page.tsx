"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


/**
 * Budget Dashboard Page (Phase 3 Frontend)
 *
 * Budget enforcement metrics and charts
 */


import React from 'react';
import { BudgetDashboard } from '@/components/neurorail/budget-dashboard';

export default function BudgetDashboardPage() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Budget Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time budget enforcement metrics: timeouts, retries, parallelism, and cost
        </p>
      </div>

      {/* Budget Dashboard Component */}
      <BudgetDashboard />
    </div>
  );
}

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

/**
 * Trace Explorer Page (Phase 3 Frontend)
 *
 * Why-View: Complete trace chain visualization
 */

"use client";

import React, { useState } from 'react';
import { TraceExplorer } from '@/components/neurorail/trace-explorer';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function TraceExplorerPage() {
  const [entityType, setEntityType] = useState<'mission' | 'plan' | 'job' | 'attempt'>('attempt');
  const [entityId, setEntityId] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Trace Explorer</h1>
        <p className="text-muted-foreground">
          Why-View: Complete trace chain from mission to resource
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle>Trace Lookup</CardTitle>
          <CardDescription>Enter entity ID to view complete trace chain</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex gap-4">
            <Select value={entityType} onValueChange={(v: any) => setEntityType(v)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mission">Mission</SelectItem>
                <SelectItem value="plan">Plan</SelectItem>
                <SelectItem value="job">Job</SelectItem>
                <SelectItem value="attempt">Attempt</SelectItem>
              </SelectContent>
            </Select>

            <Input
              placeholder="Enter entity ID (e.g., a_123)"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              className="flex-1"
            />

            <Button type="submit" disabled={!entityId}>
              Explore
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Trace Explorer */}
      {submitted && entityId && (
        <TraceExplorer entityType={entityType} entityId={entityId} />
      )}

      {!submitted && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground text-center">
              Enter an entity ID above to explore its trace chain
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

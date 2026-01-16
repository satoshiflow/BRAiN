/**
 * Business Factory Dashboard
 *
 * Template system for business processes, workflows, and automation
 */

"use client";

import React, { useState } from 'react';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import {
  useProcessStats,
  useBusinessProcesses,
  useCreateBusinessProcess,
  useDeleteBusinessProcess,
  useExecuteBusinessProcess,
  useProcessExecutions,
  type BusinessProcess,
  type ProcessStatus,
  type TriggerType,
  type ProcessExecution,
} from '@/hooks/useBusinessFactory';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Alert, AlertDescription } from '@/components/ui/alert';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Button } from '@/components/ui/button';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Input } from '@/components/ui/input';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Label } from '@/components/ui/label';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Textarea } from '@/components/ui/textarea';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Badge } from '@/components/ui/badge';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Loader2, Workflow, Plus, Play, Trash2, CheckCircle2, XCircle, AlertTriangle, TrendingUp, Activity, Clock } from 'lucide-react';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";

export default function BusinessFactoryPage() {
  const { data: stats, isLoading: statsLoading } = useProcessStats();
  
  // Show loading skeleton
  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }
  const { data: processes, isLoading: processesLoading, error: processesError } = useBusinessProcesses();
  
  // Show loading skeleton
  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }
  const { data: executions, isLoading: executionsLoading } = useProcessExecutions();
  
  // Show loading skeleton
  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }
  const [searchQuery, setSearchQuery] = useState('');

  if (statsLoading || processesLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (processesError) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Business Factory</h1>
          <p className="text-muted-foreground">
            Business process automation templates
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load business processes: {processesError.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Filter processes by search query
  const filteredProcesses = processes?.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.category.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Business Factory</h1>
        <p className="text-muted-foreground">
          Create and manage business process automation templates
        </p>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Processes</CardTitle>
              <Workflow className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_processes}</div>
              <p className="text-xs text-muted-foreground">
                {stats.active} active, {stats.draft} draft
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Executions</CardTitle>
              <Activity className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_executions}</div>
              <p className="text-xs text-muted-foreground">
                All-time executions
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.average_success_rate?.toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">
                {stats.successful_executions} successful
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Failed</CardTitle>
              <XCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.failed_executions}</div>
              <p className="text-xs text-muted-foreground">
                Failed executions
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Steps</CardTitle>
              <Clock className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_steps}</div>
              <p className="text-xs text-muted-foreground">
                Across all processes
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Category Distribution */}
      {stats && Object.keys(stats.processes_by_category).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processes by Category</CardTitle>
            <CardDescription>Distribution across business categories</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.processes_by_category).map(([category, count]) => (
                <Badge key={category} variant="secondary">
                  {category}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <Tabs defaultValue="processes" className="space-y-4">
        <TabsList>
          <TabsTrigger value="processes">
            <Workflow className="h-4 w-4 mr-2" />
            Processes
          </TabsTrigger>
          <TabsTrigger value="executions">
            <Activity className="h-4 w-4 mr-2" />
            Executions
          </TabsTrigger>
          <TabsTrigger value="create">
            <Plus className="h-4 w-4 mr-2" />
            Create Process
          </TabsTrigger>
        </TabsList>

        <TabsContent value="processes">
          {/* Search */}
          <div className="mb-4">
            <Input
              placeholder="Search processes by name, description, or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="max-w-md"
            />
          </div>

          <ProcessesList processes={filteredProcesses} />
        </TabsContent>

        <TabsContent value="executions">
          <ExecutionsList executions={executions || []} />
        </TabsContent>

        <TabsContent value="create">
          <CreateProcessForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// Processes List Component
// ============================================================================

function ProcessesList({ processes }: { processes: BusinessProcess[] }) {
  const deleteMutation = useDeleteBusinessProcess();
  const executeMutation = useExecuteBusinessProcess();

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this business process?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleExecute = (id: string) => {
    executeMutation.mutate({ process_id: id, trigger_type: 'manual' });
  };

  const getStatusColor = (status: ProcessStatus) => {
    switch (status) {
      case 'active':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'draft':
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
      case 'deprecated':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
    }
  };

  if (processes.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8">
          <Workflow className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No business processes found</p>
          <p className="text-xs text-muted-foreground mt-1">
            Create your first process to get started
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {processes.map((process) => (
        <Card key={process.id}>
          <CardContent className="p-6">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{process.name}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{process.category}</p>
                </div>
                <Badge variant="outline" className={getStatusColor(process.status)}>
                  {process.status}
                </Badge>
              </div>

              <p className="text-sm text-muted-foreground line-clamp-2">
                {process.description}
              </p>

              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{process.steps.length} steps</span>
                </div>
                <div className="flex items-center gap-1">
                  <Activity className="h-3 w-3" />
                  <span>{process.triggers.length} triggers</span>
                </div>
              </div>

              {process.success_rate !== undefined && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Success Rate</span>
                    <span className={process.success_rate >= 90 ? 'text-green-500' : process.success_rate >= 70 ? 'text-amber-500' : 'text-red-500'}>
                      {process.success_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${process.success_rate >= 90 ? 'bg-green-500' : process.success_rate >= 70 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${process.success_rate}%` }}
                    />
                  </div>
                </div>
              )}

              {process.tags && process.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {process.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {process.tags.length > 3 && (
                    <Badge variant="secondary" className="text-xs">
                      +{process.tags.length - 3}
                    </Badge>
                  )}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                {process.status === 'active' && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleExecute(process.id)}
                    disabled={executeMutation.isPending}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Execute
                  </Button>
                )}
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDelete(process.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>

              {process.execution_count !== undefined && (
                <p className="text-xs text-muted-foreground">
                  Executed {process.execution_count} times
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Executions List Component
// ============================================================================

function ExecutionsList({ executions }: { executions: ProcessExecution[] }) {
  const getStatusColor = (status: ProcessExecution['status']) => {
    switch (status) {
      case 'running':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'completed':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'failed':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'cancelled':
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  if (executions.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8">
          <Activity className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No process executions yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {executions.map((execution) => (
        <Card key={execution.id}>
          <CardContent className="p-6">
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold">{execution.process_name}</h3>
                  <Badge variant="outline" className={getStatusColor(execution.status)}>
                    {execution.status}
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Started:</span>
                    <span className="ml-2">{new Date(execution.started_at).toLocaleString()}</span>
                  </div>
                  {execution.completed_at && (
                    <div>
                      <span className="text-muted-foreground">Completed:</span>
                      <span className="ml-2">{new Date(execution.completed_at).toLocaleString()}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div>
                    Progress: {execution.steps_completed}/{execution.steps_total} steps
                  </div>
                  {execution.duration_ms && (
                    <div>
                      Duration: {(execution.duration_ms / 1000).toFixed(1)}s
                    </div>
                  )}
                </div>

                {execution.error && (
                  <Alert variant="destructive" className="mt-2">
                    <AlertDescription className="text-xs">{execution.error}</AlertDescription>
                  </Alert>
                )}

                {execution.result && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                      View Result
                    </summary>
                    <pre className="mt-2 bg-slate-950 p-2 rounded overflow-x-auto">
                      {JSON.stringify(execution.result, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Create Process Form Component
// ============================================================================

function CreateProcessForm() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState('');
  const createMutation = useCreateBusinessProcess();

  const handleCreate = () => {
    if (!name.trim() || !description.trim() || !category.trim()) return;

    const tagsArray = tags
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    createMutation.mutate(
      {
        name,
        description,
        category,
        status: 'draft',
        tags: tagsArray.length > 0 ? tagsArray : undefined,
        triggers: [],
        steps: [],
      },
      {
        onSuccess: () => {
          // Reset form
          setName('');
          setDescription('');
          setCategory('');
          setTags('');
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Business Process</CardTitle>
        <CardDescription>
          Define a reusable business process template for automation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Process Name</Label>
            <Input
              placeholder="e.g., Customer Onboarding Workflow"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Category</Label>
            <Input
              placeholder="e.g., Sales, Support, Operations"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Description</Label>
          <Textarea
            placeholder="Describe what this business process automates..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <Label>Tags (comma-separated, optional)</Label>
          <Input
            placeholder="automation, customer-facing, high-priority"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </div>

        <Alert>
          <AlertDescription className="text-xs">
            This process will be created as a draft. You can add triggers and steps after creation, then activate when ready.
          </AlertDescription>
        </Alert>

        <Button
          onClick={handleCreate}
          disabled={createMutation.isPending || !name.trim() || !description.trim() || !category.trim()}
          className="w-full"
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Process...
            </>
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Create Process
            </>
          )}
        </Button>

        {createMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>Business process created successfully as draft</AlertDescription>
          </Alert>
        )}

        {createMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{createMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

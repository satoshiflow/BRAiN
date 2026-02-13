/**
 * Policy Engine Dashboard
 *
 * Rule-based governance system for agent permissions and action authorization
 */

"use client";

import React, { useState } from 'react';
import {
  usePolicyStats,
  usePolicies,
  useEvaluatePolicy,
  useCreatePolicy,
  useUpdatePolicy,
  useDeletePolicy,
  type PolicyEffect,
  type PolicyRule,
} from '@/hooks/usePolicyEngine';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Shield, Plus, Edit, Trash2, Play, CheckCircle2, XCircle, AlertTriangle, FileText } from 'lucide-react';

export default function PolicyEnginePage() {
  const { data: stats, isLoading: statsLoading } = usePolicyStats();
  const { data: policies, isLoading: policiesLoading, error: policiesError } = usePolicies();

  if (statsLoading || policiesLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (policiesError) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Policy Engine</h1>
          <p className="text-muted-foreground">
            Rule-based governance system
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load policies: {policiesError.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Policy Engine</h1>
        <p className="text-muted-foreground">
          Rule-based governance for agent permissions and action authorization
        </p>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Policies</CardTitle>
              <Shield className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_policies}</div>
              <p className="text-xs text-muted-foreground">
                {stats.enabled_policies} enabled, {stats.disabled_policies} disabled
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">ALLOW Policies</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.policies_by_effect.allow || 0}</div>
              <p className="text-xs text-muted-foreground">
                Permission grants
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">DENY Policies</CardTitle>
              <XCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.policies_by_effect.deny || 0}</div>
              <p className="text-xs text-muted-foreground">
                Permission denials
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Evaluations</CardTitle>
              <FileText className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_evaluations}</div>
              <p className="text-xs text-muted-foreground">
                Policy evaluations performed
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="policies" className="space-y-4">
        <TabsList>
          <TabsTrigger value="policies">
            <Shield className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
          <TabsTrigger value="evaluate">
            <Play className="h-4 w-4 mr-2" />
            Test Evaluation
          </TabsTrigger>
          <TabsTrigger value="create">
            <Plus className="h-4 w-4 mr-2" />
            Create Policy
          </TabsTrigger>
        </TabsList>

        <TabsContent value="policies">
          <PoliciesList policies={policies || []} />
        </TabsContent>

        <TabsContent value="evaluate">
          <EvaluateInterface />
        </TabsContent>

        <TabsContent value="create">
          <CreatePolicyForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// Policies List Component
// ============================================================================

function PoliciesList({ policies }: { policies: PolicyRule[] }) {
  const deleteMutation = useDeletePolicy();
  const updateMutation = useUpdatePolicy();

  const handleToggleEnabled = (policy: PolicyRule) => {
    updateMutation.mutate({
      id: policy.id,
      request: { enabled: !policy.enabled },
    });
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this policy?')) {
      deleteMutation.mutate(id);
    }
  };

  const getEffectColor = (effect: PolicyEffect) => {
    switch (effect) {
      case 'allow':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'deny':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'warn':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'audit':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    }
  };

  if (policies.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8">
          <Shield className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No policies configured</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {policies.map((policy) => (
        <Card key={policy.id}>
          <CardContent className="p-6">
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold">{policy.name}</h3>
                  <Badge variant="outline" className={getEffectColor(policy.effect)}>
                    {policy.effect.toUpperCase()}
                  </Badge>
                  <Badge variant={policy.enabled ? 'default' : 'secondary'}>
                    {policy.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Priority: {policy.priority}
                  </span>
                </div>

                <p className="text-sm text-muted-foreground">{policy.description}</p>

                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    View Conditions
                  </summary>
                  <pre className="mt-2 bg-slate-950 p-2 rounded overflow-x-auto">
                    {JSON.stringify(policy.conditions, null, 2)}
                  </pre>
                </details>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleToggleEnabled(policy)}
                  disabled={updateMutation.isPending}
                >
                  {policy.enabled ? 'Disable' : 'Enable'}
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDelete(policy.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Evaluate Interface Component
// ============================================================================

function EvaluateInterface() {
  const [agentId, setAgentId] = useState('');
  const [action, setAction] = useState('');
  const [context, setContext] = useState('{}');
  const evaluateMutation = useEvaluatePolicy();

  const handleEvaluate = () => {
    if (!agentId.trim() || !action.trim()) return;

    try {
      const contextObj = JSON.parse(context);
      evaluateMutation.mutate({
        agent_id: agentId,
        action,
        context: contextObj,
      });
    } catch (error) {
      alert('Invalid JSON in context field');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Test Policy Evaluation</CardTitle>
        <CardDescription>
          Test how policies would evaluate for a specific agent action
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Agent ID</Label>
            <Input
              placeholder="e.g., ops_agent"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Action</Label>
            <Input
              placeholder="e.g., deploy_application"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Context (JSON)</Label>
          <Textarea
            placeholder='{"environment": "production", "version": "1.0.0"}'
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={5}
            className="font-mono text-sm"
          />
        </div>

        <Button
          onClick={handleEvaluate}
          disabled={evaluateMutation.isPending || !agentId.trim() || !action.trim()}
          className="w-full"
        >
          {evaluateMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Evaluating...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              Evaluate Policy
            </>
          )}
        </Button>

        {evaluateMutation.data && (
          <Alert variant={evaluateMutation.data.effect === 'deny' ? 'destructive' : 'default'}>
            <AlertDescription>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Effect:</span>
                  <Badge
                    variant={
                      evaluateMutation.data.effect === 'allow'
                        ? 'default'
                        : evaluateMutation.data.effect === 'deny'
                          ? 'destructive'
                          : 'secondary'
                    }
                  >
                    {evaluateMutation.data.effect.toUpperCase()}
                  </Badge>
                </div>
                <p>{evaluateMutation.data.reason}</p>
                {evaluateMutation.data.matched_rule && (
                  <p className="text-xs text-muted-foreground">
                    Matched rule: {evaluateMutation.data.matched_rule}
                  </p>
                )}
              </div>
            </AlertDescription>
          </Alert>
        )}

        {evaluateMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{evaluateMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Create Policy Form Component
// ============================================================================

function CreatePolicyForm() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [effect, setEffect] = useState<PolicyEffect>('allow');
  const [priority, setPriority] = useState(100);
  const [conditions, setConditions] = useState('{}');
  const createMutation = useCreatePolicy();

  const handleCreate = () => {
    if (!name.trim() || !description.trim()) return;

    try {
      const conditionsObj = JSON.parse(conditions);
      createMutation.mutate(
        {
          name,
          description,
          effect,
          priority,
          conditions: conditionsObj,
          enabled: true,
        },
        {
          onSuccess: () => {
            // Reset form
            setName('');
            setDescription('');
            setEffect('allow');
            setPriority(100);
            setConditions('{}');
          },
        }
      );
    } catch (error) {
      alert('Invalid JSON in conditions field');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Policy</CardTitle>
        <CardDescription>
          Define a new governance rule for agent actions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Policy Name</Label>
          <Input
            placeholder="e.g., Production Deployment Restriction"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label>Description</Label>
          <Textarea
            placeholder="Describe what this policy does..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Effect</Label>
            <div className="flex gap-2">
              {(['allow', 'deny', 'warn', 'audit'] as PolicyEffect[]).map((e) => (
                <Badge
                  key={e}
                  variant={effect === e ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => setEffect(e)}
                >
                  {e.toUpperCase()}
                </Badge>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Priority (higher = evaluated first)</Label>
            <Input
              type="number"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value) || 100)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Conditions (JSON)</Label>
          <Textarea
            placeholder='{"action": {"==": "deploy_application"}, "context.environment": {"==": "production"}}'
            value={conditions}
            onChange={(e) => setConditions(e.target.value)}
            rows={8}
            className="font-mono text-sm"
          />
          <p className="text-xs text-muted-foreground">
            Supported operators: ==, !=, {`>`}, {`<`}, {`>=`}, {`<=`}, contains, matches, in
          </p>
        </div>

        <Button
          onClick={handleCreate}
          disabled={createMutation.isPending || !name.trim() || !description.trim()}
          className="w-full"
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Policy...
            </>
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Create Policy
            </>
          )}
        </Button>

        {createMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>Policy created successfully</AlertDescription>
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

/**
 * Credit Dashboard - Main interface for credit management.
 *
 * Features:
 * - Agent balance overview
 * - Transaction history
 * - Credit operations (create, consume, refund)
 * - System metrics
 */

"use client";

import { useState } from "react";
import {
  useAllBalances,
  useAgentHistory,
  useCreditMetrics,
  useCreateAgent,
  useConsumeCredits,
  useRefundCredits,
  type LedgerEntry,
} from "@/hooks/useCredits";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";

export function CreditDashboard() {
  const [selectedAgent, setSelectedAgent] = useState<string>("");

  // Queries
  const { data: balances, isLoading: balancesLoading } = useAllBalances();
  const { data: metrics } = useCreditMetrics();

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Credit Management</h1>
        <p className="text-muted-foreground">
          Event-Sourced credit system with full audit trail
        </p>
      </div>

      {/* System Metrics */}
      {metrics && <SystemMetrics metrics={metrics} />}

      <Tabs defaultValue="overview" className="w-full">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="create">Create Agent</TabsTrigger>
          <TabsTrigger value="operations">Operations</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <BalanceOverview
            balances={balances}
            isLoading={balancesLoading}
            onSelectAgent={setSelectedAgent}
          />
        </TabsContent>

        {/* Create Agent Tab */}
        <TabsContent value="create">
          <CreateAgentForm />
        </TabsContent>

        {/* Operations Tab */}
        <TabsContent value="operations">
          <CreditOperations selectedAgent={selectedAgent} />
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <TransactionHistory selectedAgent={selectedAgent} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// System Metrics Component
// ============================================================================

function SystemMetrics({ metrics }: { metrics: any }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Total Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.journal.total_events}</div>
          <p className="text-xs text-muted-foreground">
            File size: {metrics.journal.file_size_mb} MB
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Event Bus</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.event_bus.total_published}</div>
          <p className="text-xs text-muted-foreground">
            Errors: {metrics.event_bus.total_subscriber_errors}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Last Replay</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {metrics.replay.replay_duration_seconds.toFixed(2)}s
          </div>
          <p className="text-xs text-muted-foreground">
            Integrity errors: {metrics.replay.integrity_errors_count}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// Balance Overview Component
// ============================================================================

function BalanceOverview({ balances, isLoading, onSelectAgent }: any) {
  if (isLoading) return <div>Loading balances...</div>;
  if (!balances) return <div>No data</div>;

  const sortedAgents = Object.entries(balances.balances).sort(
    ([, a]: any, [, b]: any) => b - a
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Balances</CardTitle>
        <CardDescription>
          {balances.total_agents} agents with total credits
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {sortedAgents.map(([agentId, balance]: any) => (
            <div
              key={agentId}
              className="flex items-center justify-between rounded-lg border p-3 cursor-pointer hover:bg-accent"
              onClick={() => onSelectAgent(agentId)}
            >
              <div>
                <p className="font-medium">{agentId}</p>
              </div>
              <Badge variant={balance > 50 ? "default" : balance > 20 ? "secondary" : "destructive"}>
                {balance.toFixed(1)} credits
              </Badge>
            </div>
          ))}

          {sortedAgents.length === 0 && (
            <p className="text-center text-muted-foreground py-8">
              No agents created yet. Create one in the "Create Agent" tab.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Create Agent Form
// ============================================================================

function CreateAgentForm() {
  const [agentId, setAgentId] = useState("");
  const [skillLevel, setSkillLevel] = useState("0.8");
  const createAgent = useCreateAgent();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createAgent.mutate({
      agent_id: agentId,
      skill_level: parseFloat(skillLevel),
    });
    setAgentId("");
    setSkillLevel("0.8");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create Agent</CardTitle>
        <CardDescription>
          Allocate initial credits based on skill level (skill_level × 100)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="agentId">Agent ID</Label>
            <Input
              id="agentId"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              placeholder="agent_123"
              required
            />
          </div>

          <div>
            <Label htmlFor="skillLevel">Skill Level (0.0 - 1.0)</Label>
            <Input
              id="skillLevel"
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={skillLevel}
              onChange={(e) => setSkillLevel(e.target.value)}
              required
            />
            <p className="text-sm text-muted-foreground mt-1">
              Initial credits: {(parseFloat(skillLevel) * 100).toFixed(1)}
            </p>
          </div>

          <Button type="submit" disabled={createAgent.isPending}>
            {createAgent.isPending ? "Creating..." : "Create Agent"}
          </Button>

          {createAgent.isSuccess && (
            <Alert>
              <AlertDescription>
                Agent created successfully with {createAgent.data.initial_credits} credits
              </AlertDescription>
            </Alert>
          )}

          {createAgent.isError && (
            <Alert variant="destructive">
              <AlertDescription>{createAgent.error.message}</AlertDescription>
            </Alert>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Credit Operations Component
// ============================================================================

function CreditOperations({ selectedAgent }: { selectedAgent: string }) {
  const [amount, setAmount] = useState("10");
  const [reason, setReason] = useState("");
  const consumeCredits = useConsumeCredits();
  const refundCredits = useRefundCredits();

  const handleConsume = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;
    consumeCredits.mutate({
      agent_id: selectedAgent,
      amount: parseFloat(amount),
      reason: reason || "Manual consumption",
    });
    setAmount("10");
    setReason("");
  };

  const handleRefund = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;
    refundCredits.mutate({
      agent_id: selectedAgent,
      amount: parseFloat(amount),
      reason: reason || "Manual refund",
    });
    setAmount("10");
    setReason("");
  };

  if (!selectedAgent) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-muted-foreground">
            Select an agent from the Overview tab to perform operations
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Consume Credits */}
      <Card>
        <CardHeader>
          <CardTitle>Consume Credits</CardTitle>
          <CardDescription>Agent: {selectedAgent}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleConsume} className="space-y-4">
            <div>
              <Label htmlFor="consumeAmount">Amount</Label>
              <Input
                id="consumeAmount"
                type="number"
                step="0.1"
                min="0.1"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>

            <div>
              <Label htmlFor="consumeReason">Reason</Label>
              <Input
                id="consumeReason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Mission execution"
              />
            </div>

            <Button type="submit" disabled={consumeCredits.isPending} variant="destructive">
              {consumeCredits.isPending ? "Consuming..." : "Consume Credits"}
            </Button>

            {consumeCredits.isError && (
              <Alert variant="destructive">
                <AlertDescription>{consumeCredits.error.message}</AlertDescription>
              </Alert>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Refund Credits */}
      <Card>
        <CardHeader>
          <CardTitle>Refund Credits</CardTitle>
          <CardDescription>Agent: {selectedAgent}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRefund} className="space-y-4">
            <div>
              <Label htmlFor="refundAmount">Amount</Label>
              <Input
                id="refundAmount"
                type="number"
                step="0.1"
                min="0.1"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>

            <div>
              <Label htmlFor="refundReason">Reason</Label>
              <Input
                id="refundReason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Failed mission"
              />
            </div>

            <Button type="submit" disabled={refundCredits.isPending}>
              {refundCredits.isPending ? "Refunding..." : "Refund Credits"}
            </Button>

            {refundCredits.isError && (
              <Alert variant="destructive">
                <AlertDescription>{refundCredits.error.message}</AlertDescription>
              </Alert>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// Transaction History Component
// ============================================================================

function TransactionHistory({ selectedAgent }: { selectedAgent: string }) {
  const { data: history, isLoading } = useAgentHistory(selectedAgent, 20, {
    enabled: !!selectedAgent,
  });

  if (!selectedAgent) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-muted-foreground">
            Select an agent from the Overview tab to view history
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) return <div>Loading history...</div>;
  if (!history) return <div>No history</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transaction History</CardTitle>
        <CardDescription>
          Agent: {selectedAgent} ({history.total_entries} entries)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {history.history.map((entry: LedgerEntry) => (
            <div key={entry.event_id} className="flex items-center justify-between border-b pb-2">
              <div>
                <p className="font-medium">{entry.reason}</p>
                <p className="text-sm text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleString()}
                </p>
              </div>
              <div className="text-right">
                <p className={entry.amount > 0 ? "text-green-600" : "text-red-600"}>
                  {entry.amount > 0 ? "+" : ""}
                  {entry.amount.toFixed(1)}
                </p>
                <p className="text-sm text-muted-foreground">
                  Balance: {entry.balance_after.toFixed(1)}
                </p>
              </div>
            </div>
          ))}

          {history.history.length === 0 && (
            <p className="text-center text-muted-foreground py-8">No transactions yet</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

"use client";

import { useState } from "react";
import {
  useAgentBalance,
  useAllBalances,
  useAgentHistory,
  useCreditMetrics,
  useCreateAgent,
  useConsumeCredits,
  useRefundCredits,
} from "@/hooks/useCredits";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Coins, TrendingUp, TrendingDown, Activity, Clock, Database } from "lucide-react";

export default function CreditsPage() {
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [agentIdInput, setAgentIdInput] = useState<string>("");
  const [newAgentId, setNewAgentId] = useState<string>("");
  const [skillLevel, setSkillLevel] = useState<string>("0.5");

  const { data: allBalances, isLoading: balancesLoading } = useAllBalances();
  const { data: balance } = useAgentBalance(selectedAgentId || undefined);
  const { data: history, isLoading: historyLoading } = useAgentHistory(selectedAgentId || undefined, 20);
  const { data: metrics, isLoading: metricsLoading } = useCreditMetrics();

  const createAgent = useCreateAgent();
  const consumeCredits = useConsumeCredits();
  const refundCredits = useRefundCredits();

  const handleViewAgent = () => {
    if (agentIdInput.trim()) {
      setSelectedAgentId(agentIdInput.trim());
    }
  };

  const handleCreateAgent = () => {
    if (newAgentId.trim() && parseFloat(skillLevel) >= 0 && parseFloat(skillLevel) <= 1) {
      createAgent.mutate({
        agent_id: newAgentId.trim(),
        skill_level: parseFloat(skillLevel),
        actor_id: "control_deck",
      });
      setNewAgentId("");
      setSkillLevel("0.5");
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Credits System</h2>
          <p className="text-muted-foreground">
            Event Sourcing based credit management for agents
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          Event Sourcing
        </Badge>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <Coins className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {balancesLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{allBalances?.total_agents || 0}</div>
                <p className="text-xs text-muted-foreground">Registered agents</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Journal Events</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{metrics?.journal.total_events || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {metrics?.journal.file_size_mb.toFixed(2) || 0} MB
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Event Bus</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{metrics?.event_bus.total_published || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {metrics?.event_bus.total_subscriber_errors || 0} errors
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Replay</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{metrics?.replay.total_events || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {metrics?.replay.replay_duration_seconds.toFixed(2) || 0}s duration
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="balances" className="space-y-4">
        <TabsList>
          <TabsTrigger value="balances">All Balances</TabsTrigger>
          <TabsTrigger value="agent">Agent Details</TabsTrigger>
          <TabsTrigger value="create">Create Agent</TabsTrigger>
          <TabsTrigger value="metrics">System Metrics</TabsTrigger>
        </TabsList>

        {/* All Balances Tab */}
        <TabsContent value="balances" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Agent Balances</CardTitle>
              <CardDescription>Credit balances for all registered agents</CardDescription>
            </CardHeader>
            <CardContent>
              {balancesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : allBalances && Object.keys(allBalances.balances).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(allBalances.balances).map(([agentId, balance]) => (
                    <div
                      key={agentId}
                      className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent"
                    >
                      <div className="flex items-center gap-2">
                        <Coins className="h-4 w-4 text-muted-foreground" />
                        <span className="font-mono text-sm">{agentId}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{balance.toFixed(2)}</span>
                        <span className="text-sm text-muted-foreground">credits</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No agents registered yet
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Agent Details Tab */}
        <TabsContent value="agent" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Agent Details</CardTitle>
              <CardDescription>View balance and transaction history for an agent</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Agent ID Input */}
              <div className="flex items-end gap-4">
                <div className="flex-1 space-y-2">
                  <Label htmlFor="agent-id">Agent ID</Label>
                  <Input
                    id="agent-id"
                    placeholder="e.g., agent_001"
                    value={agentIdInput}
                    onChange={(e) => setAgentIdInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleViewAgent()}
                  />
                </div>
                <Button onClick={handleViewAgent} disabled={!agentIdInput.trim()}>
                  View Agent
                </Button>
              </div>

              {/* Agent Balance */}
              {selectedAgentId && balance && (
                <div className="space-y-4">
                  <Card className="bg-primary/5">
                    <CardContent className="flex items-center justify-between pt-6">
                      <div>
                        <p className="text-sm text-muted-foreground">Current Balance</p>
                        <p className="text-3xl font-bold">{balance.balance.toFixed(2)}</p>
                      </div>
                      <Coins className="h-12 w-12 text-primary/50" />
                    </CardContent>
                  </Card>

                  {/* Transaction History */}
                  <div>
                    <h3 className="mb-4 text-lg font-semibold">Transaction History</h3>
                    {historyLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                      </div>
                    ) : history && history.history.length > 0 ? (
                      <div className="space-y-2">
                        {history.history.map((entry) => (
                          <div
                            key={entry.event_id}
                            className="flex items-start justify-between rounded-lg border p-3"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                {entry.amount > 0 ? (
                                  <TrendingUp className="h-4 w-4 text-green-500" />
                                ) : (
                                  <TrendingDown className="h-4 w-4 text-red-500" />
                                )}
                                <span className="text-sm font-medium">{entry.reason}</span>
                              </div>
                              <p className="text-xs text-muted-foreground">
                                {new Date(entry.timestamp).toLocaleString()}
                              </p>
                              {entry.mission_id && (
                                <p className="text-xs text-muted-foreground">
                                  Mission: {entry.mission_id}
                                </p>
                              )}
                            </div>
                            <div className="text-right">
                              <p
                                className={`text-lg font-bold ${
                                  entry.amount > 0 ? "text-green-500" : "text-red-500"
                                }`}
                              >
                                {entry.amount > 0 ? "+" : ""}
                                {entry.amount.toFixed(2)}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Balance: {entry.balance_after.toFixed(2)}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="py-8 text-center text-sm text-muted-foreground">
                        No transaction history
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Create Agent Tab */}
        <TabsContent value="create" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Create Agent</CardTitle>
              <CardDescription>
                Create a new agent with initial credits based on skill level
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new-agent-id">Agent ID</Label>
                <Input
                  id="new-agent-id"
                  placeholder="e.g., agent_002"
                  value={newAgentId}
                  onChange={(e) => setNewAgentId(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="skill-level">Skill Level (0.0 - 1.0)</Label>
                <Input
                  id="skill-level"
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={skillLevel}
                  onChange={(e) => setSkillLevel(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Initial credits = skill level × 100
                  {parseFloat(skillLevel) >= 0 && parseFloat(skillLevel) <= 1
                    ? ` = ${(parseFloat(skillLevel) * 100).toFixed(1)} credits`
                    : ""}
                </p>
              </div>

              <Button
                onClick={handleCreateAgent}
                disabled={
                  !newAgentId.trim() ||
                  parseFloat(skillLevel) < 0 ||
                  parseFloat(skillLevel) > 1 ||
                  createAgent.isPending
                }
                className="w-full"
              >
                {createAgent.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  "Create Agent"
                )}
              </Button>

              {createAgent.isSuccess && (
                <div className="rounded-lg bg-green-500/10 p-4 text-sm text-green-500">
                  Agent created successfully!
                </div>
              )}

              {createAgent.isError && (
                <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
                  Error: {createAgent.error.message}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* System Metrics Tab */}
        <TabsContent value="metrics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Journal Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Event Journal</CardTitle>
                <CardDescription>Persistent event log metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {metricsLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : metrics ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Events:</span>
                      <span className="font-medium">{metrics.journal.total_events}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">File Size:</span>
                      <span className="font-medium">{metrics.journal.file_size_mb.toFixed(2)} MB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Violations:</span>
                      <span className="font-medium">{metrics.journal.idempotency_violations}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">File Path:</span>
                      <span className="font-mono text-xs">{metrics.journal.file_path}</span>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            {/* Event Bus Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Event Bus</CardTitle>
                <CardDescription>Pub/sub messaging metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {metricsLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : metrics ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Published:</span>
                      <span className="font-medium">{metrics.event_bus.total_published}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Errors:</span>
                      <span className="font-medium">{metrics.event_bus.total_subscriber_errors}</span>
                    </div>
                    <div className="mt-2">
                      <p className="mb-1 text-xs text-muted-foreground">Subscribers:</p>
                      <div className="space-y-1">
                        {Object.entries(metrics.event_bus.subscribers_by_type).map(([type, count]) => (
                          <div key={type} className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{type}:</span>
                            <span className="font-mono">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            {/* Replay Metrics */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Event Replay</CardTitle>
                <CardDescription>State reconstruction metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {metricsLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : metrics ? (
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Total Events</p>
                      <p className="text-2xl font-bold">{metrics.replay.total_events}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Duration</p>
                      <p className="text-2xl font-bold">
                        {metrics.replay.replay_duration_seconds.toFixed(2)}s
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Integrity Errors</p>
                      <p className="text-2xl font-bold">{metrics.replay.integrity_errors_count}</p>
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

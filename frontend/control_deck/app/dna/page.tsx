"use client";

import { useState } from "react";
import {
  useAgentDNAHistory,
  useCreateSnapshot,
  useMutateAgent,
  useLatestSnapshot,
  useFitnessProgression,
} from "@/hooks/useDNA";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Dna, TrendingUp, GitBranch, Zap, History } from "lucide-react";

export default function DNAPage() {
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [agentIdInput, setAgentIdInput] = useState<string>("");
  const [mutationStrategy, setMutationStrategy] = useState<string>("random");

  const { data: history, isLoading: historyLoading } = useAgentDNAHistory(selectedAgentId || undefined);
  const latestSnapshot = useLatestSnapshot(selectedAgentId || undefined);
  const fitnessProgression = useFitnessProgression(selectedAgentId || undefined);

  const createSnapshot = useCreateSnapshot();
  const mutateAgent = useMutateAgent();

  const handleViewAgent = () => {
    if (agentIdInput.trim()) {
      setSelectedAgentId(agentIdInput.trim());
    }
  };

  const handleMutate = () => {
    if (selectedAgentId) {
      mutateAgent.mutate({
        agentId: selectedAgentId,
        request: {
          mutation_strategy: mutationStrategy as 'random' | 'gradient' | 'crossover',
          mutation_rate: 0.1,
        },
      });
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">DNA Evolution</h2>
          <p className="text-muted-foreground">
            Agent genetic optimization and parameter evolution
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          <Dna className="mr-1 h-3 w-3" />
          Genetic Algorithm
        </Badge>
      </div>

      {/* Agent Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Selection</CardTitle>
          <CardDescription>Enter an agent ID to view its evolution history</CardDescription>
        </CardHeader>
        <CardContent className="flex items-end gap-4">
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
            View Evolution
          </Button>
        </CardContent>
      </Card>

      {/* Main Content */}
      {selectedAgentId && (
        <>
          {historyLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : history ? (
            <>
              {/* Overview Cards */}
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Generation</CardTitle>
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{history.current_generation}</div>
                    <p className="text-xs text-muted-foreground">Current generation</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Snapshots</CardTitle>
                    <History className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{history.total_snapshots}</div>
                    <p className="text-xs text-muted-foreground">Total snapshots</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Fitness Score</CardTitle>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {latestSnapshot?.fitness_score?.toFixed(3) || "N/A"}
                    </div>
                    <p className="text-xs text-muted-foreground">Latest score</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Improvement</CardTitle>
                    <Zap className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    {fitnessProgression.length >= 2 ? (
                      <>
                        <div className="text-2xl font-bold">
                          {(
                            ((fitnessProgression[fitnessProgression.length - 1].fitness -
                              fitnessProgression[0].fitness) /
                              fitnessProgression[0].fitness) *
                            100
                          ).toFixed(1)}
                          %
                        </div>
                        <p className="text-xs text-muted-foreground">Since generation 0</p>
                      </>
                    ) : (
                      <div className="text-sm text-muted-foreground">Not enough data</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Tabs */}
              <Tabs defaultValue="history" className="space-y-4">
                <TabsList>
                  <TabsTrigger value="history">Evolution History</TabsTrigger>
                  <TabsTrigger value="mutate">Mutate Agent</TabsTrigger>
                  <TabsTrigger value="fitness">Fitness Progression</TabsTrigger>
                </TabsList>

                {/* Evolution History Tab */}
                <TabsContent value="history" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Evolution Timeline</CardTitle>
                      <CardDescription>
                        Complete history of parameter snapshots and mutations
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {history.snapshots.length > 0 ? (
                        <div className="space-y-3">
                          {history.snapshots
                            .slice()
                            .reverse()
                            .map((snapshot) => (
                              <div
                                key={snapshot.snapshot_id}
                                className="rounded-lg border p-4 hover:bg-accent"
                              >
                                <div className="flex items-start justify-between">
                                  <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                      <Badge variant="outline">Gen {snapshot.generation}</Badge>
                                      {snapshot.mutation_applied && (
                                        <Badge variant="secondary">{snapshot.mutation_applied}</Badge>
                                      )}
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                      {new Date(snapshot.timestamp).toLocaleString()}
                                    </p>
                                    <p className="font-mono text-xs text-muted-foreground">
                                      ID: {snapshot.snapshot_id}
                                    </p>
                                  </div>
                                  <div className="text-right">
                                    {snapshot.fitness_score !== undefined && (
                                      <>
                                        <p className="text-sm text-muted-foreground">Fitness</p>
                                        <p className="text-xl font-bold">
                                          {snapshot.fitness_score.toFixed(3)}
                                        </p>
                                      </>
                                    )}
                                  </div>
                                </div>

                                {/* Parameters Preview */}
                                <div className="mt-3 rounded bg-muted p-2">
                                  <p className="mb-1 text-xs font-medium">Parameters:</p>
                                  <div className="max-h-20 overflow-auto text-xs">
                                    <pre>{JSON.stringify(snapshot.params, null, 2)}</pre>
                                  </div>
                                </div>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <div className="py-8 text-center text-sm text-muted-foreground">
                          No snapshots found
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Mutate Agent Tab */}
                <TabsContent value="mutate" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Generate Mutation</CardTitle>
                      <CardDescription>
                        Apply genetic mutations to evolve agent parameters
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="mutation-strategy">Mutation Strategy</Label>
                        <Select value={mutationStrategy} onValueChange={setMutationStrategy}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="random">Random Mutation</SelectItem>
                            <SelectItem value="gradient">Gradient-Based</SelectItem>
                            <SelectItem value="crossover">Crossover</SelectItem>
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                          {mutationStrategy === "random" &&
                            "Randomly perturb parameters within bounds"}
                          {mutationStrategy === "gradient" &&
                            "Follow fitness gradient for optimization"}
                          {mutationStrategy === "crossover" &&
                            "Combine traits from multiple snapshots"}
                        </p>
                      </div>

                      <Button
                        onClick={handleMutate}
                        disabled={mutateAgent.isPending || !latestSnapshot}
                        className="w-full"
                      >
                        {mutateAgent.isPending ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Mutating...
                          </>
                        ) : (
                          <>
                            <Dna className="mr-2 h-4 w-4" />
                            Apply Mutation
                          </>
                        )}
                      </Button>

                      {mutateAgent.isSuccess && (
                        <div className="rounded-lg bg-green-500/10 p-4 text-sm text-green-500">
                          Mutation applied successfully! New generation created.
                        </div>
                      )}

                      {mutateAgent.isError && (
                        <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
                          Error: {mutateAgent.error.message}
                        </div>
                      )}

                      {latestSnapshot && (
                        <div className="rounded-lg border p-4">
                          <p className="mb-2 text-sm font-medium">Current Parameters:</p>
                          <div className="max-h-40 overflow-auto rounded bg-muted p-2 text-xs">
                            <pre>{JSON.stringify(latestSnapshot.params, null, 2)}</pre>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Fitness Progression Tab */}
                <TabsContent value="fitness" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Fitness Over Generations</CardTitle>
                      <CardDescription>
                        Evolution of fitness score across generations
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {fitnessProgression.length > 0 ? (
                        <div className="space-y-4">
                          {/* Simple bar chart */}
                          <div className="space-y-2">
                            {fitnessProgression.map((point, index) => (
                              <div key={index} className="flex items-center gap-4">
                                <span className="w-16 text-sm text-muted-foreground">
                                  Gen {point.generation}
                                </span>
                                <div className="flex-1">
                                  <div className="h-8 rounded bg-secondary">
                                    <div
                                      className="h-8 rounded bg-primary transition-all"
                                      style={{
                                        width: `${
                                          (point.fitness /
                                            Math.max(...fitnessProgression.map((p) => p.fitness))) *
                                          100
                                        }%`,
                                      }}
                                    />
                                  </div>
                                </div>
                                <span className="w-20 text-right font-mono text-sm">
                                  {point.fitness.toFixed(3)}
                                </span>
                              </div>
                            ))}
                          </div>

                          {/* Statistics */}
                          <div className="grid gap-4 md:grid-cols-3">
                            <div className="rounded-lg border p-3">
                              <p className="text-sm text-muted-foreground">Best Fitness</p>
                              <p className="text-lg font-bold">
                                {Math.max(...fitnessProgression.map((p) => p.fitness)).toFixed(3)}
                              </p>
                            </div>
                            <div className="rounded-lg border p-3">
                              <p className="text-sm text-muted-foreground">Average Fitness</p>
                              <p className="text-lg font-bold">
                                {(
                                  fitnessProgression.reduce((sum, p) => sum + p.fitness, 0) /
                                  fitnessProgression.length
                                ).toFixed(3)}
                              </p>
                            </div>
                            <div className="rounded-lg border p-3">
                              <p className="text-sm text-muted-foreground">Trend</p>
                              <p className="text-lg font-bold">
                                {fitnessProgression.length >= 2 &&
                                fitnessProgression[fitnessProgression.length - 1].fitness >
                                  fitnessProgression[0].fitness
                                  ? "📈 Improving"
                                  : "📉 Declining"}
                              </p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="py-8 text-center text-sm text-muted-foreground">
                          No fitness data available
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No history found for this agent
            </div>
          )}
        </>
      )}
    </div>
  );
}

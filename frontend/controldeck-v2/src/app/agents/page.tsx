"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card";
import { Button } from "@ui-core/components/button";
import { Badge } from "@ui-core/components/badge";
import { Switch } from "@ui-core/components/switch";
import { Input, Label } from "@ui-core/components/input";
import { Alert, AlertDescription } from "@ui-core/components/alert";
import {
  Dialog,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@ui-core/components/dialog";
import { 
  Bot, 
  Plus, 
  Activity,
  CheckCircle,
  AlertCircle,
  XCircle,
  Clock,
  Trash2,
  RefreshCw,
  Cpu,
  Wifi,
  WifiOff,
  Terminal
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de";

interface Agent {
  id: string;
  agent_id: string;
  name: string;
  description?: string;
  status: "registered" | "active" | "degraded" | "offline" | "maintenance" | "terminated";
  agent_type: string;
  version?: string;
  capabilities: string[];
  last_heartbeat?: string;
  tasks_completed: number;
  tasks_failed: number;
  host?: string;
  registered_at: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRegisterDialog, setShowRegisterDialog] = useState(false);
  const [message, setMessage] = useState("");
  const [newAgent, setNewAgent] = useState({
    agent_id: "",
    name: "",
    description: "",
    agent_type: "worker",
    capabilities: "",
  });

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgents(data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch agents");
    } finally {
      setLoading(false);
    }
  };

  const registerAgent = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agents/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...newAgent,
          capabilities: newAgent.capabilities.split(",").map(c => c.trim()).filter(Boolean),
        }),
      });
      
      if (res.ok) {
        setShowRegisterDialog(false);
        setNewAgent({ agent_id: "", name: "", description: "", agent_type: "worker", capabilities: "" });
        fetchAgents();
        setMessage("Agent registered successfully!");
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (e) {
      setMessage("Failed to register agent");
    }
  };

  const terminateAgent = async (agentId: string) => {
    if (!confirm("Terminate this agent?")) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/agents/${agentId}/terminate`, {
        method: "POST",
      });
      
      if (res.ok) {
        fetchAgents();
        setMessage("Agent terminated");
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (e) {
      setMessage("Failed to terminate agent");
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "degraded":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "offline":
        return <WifiOff className="h-4 w-4 text-red-500" />;
      case "terminated":
        return <XCircle className="h-4 w-4 text-gray-400" />;
      default:
        return <Activity className="h-4 w-4 text-blue-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-500/10 text-green-500";
      case "degraded":
        return "bg-yellow-500/10 text-yellow-500";
      case "offline":
        return "bg-red-500/10 text-red-500";
      case "terminated":
        return "bg-gray-500/10 text-gray-400";
      default:
        return "bg-blue-500/10 text-blue-500";
    }
  };

  const activeAgents = agents.filter(a => a.status === "active").length;
  const offlineAgents = agents.filter(a => a.status === "offline").length;
  const totalTasks = agents.reduce((sum, a) => sum + a.tasks_completed, 0);

  return (
    <DashboardLayout title="Agent Network" subtitle="Manage and monitor agents">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Agents</p>
                  <p className="text-2xl font-bold">{agents.length}</p>
                </div>
                <Bot className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active</p>
                  <p className="text-2xl font-bold text-green-500">{activeAgents}</p>
                </div>
                <Wifi className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Offline</p>
                  <p className="text-2xl font-bold text-red-500">{offlineAgents}</p>
                </div>
                <WifiOff className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Tasks Completed</p>
                  <p className="text-2xl font-bold">{totalTasks}</p>
                </div>
                <Terminal className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex justify-between items-center">
          <div>
            {message && (
              <Alert className="bg-green-500/10 border-green-500/20 w-fit">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <AlertDescription className="text-green-700">{message}</AlertDescription>
              </Alert>
            )}
          </div>
          <Button onClick={() => setShowRegisterDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Register Agent
          </Button>
          
          <Dialog open={showRegisterDialog} onOpenChange={setShowRegisterDialog}>
            <DialogHeader>
              <DialogTitle>Register New Agent</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Agent ID</Label>
                <Input
                  value={newAgent.agent_id}
                  onChange={(e) => setNewAgent({...newAgent, agent_id: e.target.value})}
                  placeholder="e.g., agent-001"
                />
              </div>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={newAgent.name}
                  onChange={(e) => setNewAgent({...newAgent, name: e.target.value})}
                  placeholder="Agent display name"
                />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <select
                  value={newAgent.agent_type}
                  onChange={(e) => setNewAgent({...newAgent, agent_type: e.target.value})}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                >
                  <option value="worker">Worker</option>
                  <option value="supervisor">Supervisor</option>
                  <option value="specialist">Specialist</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Capabilities (comma-separated)</Label>
                <Input
                  value={newAgent.capabilities}
                  onChange={(e) => setNewAgent({...newAgent, capabilities: e.target.value})}
                  placeholder="e.g., http, file, analysis"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRegisterDialog(false)}>Cancel</Button>
              <Button onClick={registerAgent}>Register</Button>
            </DialogFooter>
          </Dialog>
        </div>

        {/* Agents Grid */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Active Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : agents.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No agents registered yet</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {agents.map((agent) => (
                  <Card key={agent.id} className="border-l-4 border-l-primary">
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <Bot className="h-5 w-5 text-primary" />
                          <div>
                            <p className="font-medium">{agent.name}</p>
                            <p className="text-xs text-muted-foreground">{agent.agent_id}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(agent.status)}
                          <Badge variant="outline" className={getStatusColor(agent.status)}>
                            {agent.status}
                          </Badge>
                        </div>
                      </div>

                      <div className="mt-3 space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Cpu className="h-3 w-3" />
                          <span className="capitalize">{agent.agent_type}</span>
                          {agent.version && <span>v{agent.version}</span>}
                        </div>
                        
                        {agent.capabilities.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {agent.capabilities.slice(0, 3).map((cap) => (
                              <Badge key={cap} variant="secondary" className="text-xs">
                                {cap}
                              </Badge>
                            ))}
                            {agent.capabilities.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{agent.capabilities.length - 3}
                              </Badge>
                            )}
                          </div>
                        )}

                        <div className="flex items-center justify-between pt-2 border-t">
                          <div className="text-xs text-muted-foreground">
                            <span className="text-green-500">{agent.tasks_completed}</span> done
                            {agent.tasks_failed > 0 && (
                              <span className="text-red-500 ml-2">{agent.tasks_failed} failed</span>
                            )}
                          </div>
                          {agent.status !== "terminated" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive"
                              onClick={() => terminateAgent(agent.agent_id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

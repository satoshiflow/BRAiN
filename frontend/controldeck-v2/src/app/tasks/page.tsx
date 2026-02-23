"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card";
import { Button } from "@ui-core/components/button";
import { Badge } from "@ui-core/components/badge";
import { Progress } from "@ui-core/components/progress";
import { Input, Label } from "@ui-core/components/input";
import { Alert, AlertDescription } from "@ui-core/components/alert";
import {
  Dialog,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@ui-core/components/dialog";
import { 
  ListTodo,
  Plus,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  Trash2,
  Pause,
  TrendingUp,
  Calendar,
  Layers
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de";

interface Task {
  id: string;
  task_id: string;
  name: string;
  status: "pending" | "scheduled" | "claimed" | "running" | "completed" | "failed" | "cancelled";
  priority: number;
  task_type: string;
  claimed_by?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  retry_count: number;
  max_retries: number;
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState({
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
  });
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [message, setMessage] = useState("");
  const [newTask, setNewTask] = useState({
    name: "",
    task_type: "generic",
    priority: "50",
    payload: "{}",
  });

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tasks?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data.items || []);
        setStats({
          pending: data.items?.filter((t: Task) => t.status === "pending").length || 0,
          running: data.items?.filter((t: Task) => t.status === "running").length || 0,
          completed: data.items?.filter((t: Task) => t.status === "completed").length || 0,
          failed: data.items?.filter((t: Task) => t.status === "failed").length || 0,
        });
      }
    } catch (e) {
      console.error("Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  };

  const createTask = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newTask.name,
          task_type: newTask.task_type,
          priority: parseInt(newTask.priority),
          payload: JSON.parse(newTask.payload),
        }),
      });
      
      if (res.ok) {
        setShowCreateDialog(false);
        setNewTask({ name: "", task_type: "generic", priority: "50", payload: "{}" });
        fetchTasks();
        setMessage("Task created!");
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (e) {
      setMessage("Failed to create task");
    }
  };

  const cancelTask = async (taskId: string) => {
    if (!confirm("Cancel this task?")) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/tasks/${taskId}/cancel`, {
        method: "POST",
      });
      
      if (res.ok) {
        fetchTasks();
        setMessage("Task cancelled");
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (e) {
      setMessage("Failed to cancel task");
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="h-4 w-4 text-blue-500" />;
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "cancelled":
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-blue-500/10 text-blue-500";
      case "completed":
        return "bg-green-500/10 text-green-500";
      case "failed":
        return "bg-red-500/10 text-red-500";
      case "cancelled":
        return "bg-gray-500/10 text-gray-400";
      default:
        return "bg-yellow-500/10 text-yellow-500";
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 75) return "text-red-500";
    if (priority >= 50) return "text-yellow-500";
    return "text-blue-500";
  };

  return (
    <DashboardLayout title="Task Queue" subtitle="Manage and monitor tasks">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending</p>
                  <p className="text-2xl font-bold text-yellow-500">{stats.pending}</p>
                </div>
                <Clock className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Running</p>
                  <p className="text-2xl font-bold text-blue-500">{stats.running}</p>
                </div>
                <Play className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Completed</p>
                  <p className="text-2xl font-bold text-green-500">{stats.completed}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Failed</p>
                  <p className="text-2xl font-bold text-red-500">{stats.failed}</p>
                </div>
                <XCircle className="h-8 w-8 text-red-500" />
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
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Task
              </Button>
            
            
              <DialogHeader>
                <DialogTitle>Create New Task</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Task Name</Label>
                  <Input
                    value={newTask.name}
                    onChange={(e) => setNewTask({...newTask, name: e.target.value})}
                    placeholder="Enter task name"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Input
                    value={newTask.task_type}
                    onChange={(e) => setNewTask({...newTask, task_type: e.target.value})}
                    placeholder="generic, process, analysis..."
                  />
                </div>
                <div className="space-y-2">
                  <Label>Priority (10-100)</Label>
                  <Input
                    type="number"
                    value={newTask.priority}
                    onChange={(e) => setNewTask({...newTask, priority: e.target.value})}
                    min="10"
                    max="100"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Payload (JSON)</Label>
                  <textarea
                    value={newTask.payload}
                    onChange={(e) => setNewTask({...newTask, payload: e.target.value})}
                    className="w-full h-24 p-2 rounded-md border border-input bg-background font-mono text-sm"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                <Button onClick={createTask}>Create</Button>
              </DialogFooter>
            
          </Dialog>
        </div>

        {/* Tasks List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Task Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : tasks.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <ListTodo className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No tasks in queue</p>
              </div>
            ) : (
              <div className="space-y-2">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {getStatusIcon(task.status)}
                      <div>
                        <p className="font-medium">{task.name}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span className={getPriorityColor(task.priority)}>
                            P{task.priority}
                          </span>
                          <span>•</span>
                          <span className="capitalize">{task.task_type}</span>
                          {task.claimed_by && (
                            <>
                              <span>•</span>
                              <span>claimed by {task.claimed_by}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className={getStatusColor(task.status)}>
                        {task.status}
                      </Badge>
                      
                      {task.retry_count > 0 && (
                        <span className="text-xs text-orange-500">
                          Retry {task.retry_count}/{task.max_retries}
                        </span>
                      )}
                      
                      {["pending", "scheduled", "claimed"].includes(task.status) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() => cancelTask(task.task_id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

/**
 * Fleet Management Dashboard
 *
 * Multi-robot fleet coordination and management system
 */

"use client";

import React, { useState } from 'react';
import {
  useFleetStats,
  useRobots,
  useRegisterRobot,
  useUpdateRobot,
  useDeregisterRobot,
  useAssignTask,
  useCoordinationZones,
  type Robot,
  type RobotStatus,
} from '@/hooks/useFleetManagement';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Cpu, Plus, Activity, Battery, MapPin, Trash2, Send, Grid3x3, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function FleetManagementPage() {
  const { data: stats, isLoading: statsLoading } = useFleetStats();
  const { data: robots, isLoading: robotsLoading, error: robotsError } = useRobots();
  const { data: zones, isLoading: zonesLoading } = useCoordinationZones();

  if (statsLoading || robotsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (robotsError) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Fleet Management</h1>
          <p className="text-muted-foreground">
            Multi-robot fleet coordination
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load fleet data: {robotsError.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Fleet Management</h1>
        <p className="text-muted-foreground">
          Multi-robot fleet coordination and task distribution
        </p>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Robots</CardTitle>
              <Cpu className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_robots}</div>
              <p className="text-xs text-muted-foreground">
                Fleet size
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active</CardTitle>
              <Activity className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.active}</div>
              <p className="text-xs text-muted-foreground">
                Currently working
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Idle</CardTitle>
              <Battery className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.idle}</div>
              <p className="text-xs text-muted-foreground">
                Available for tasks
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Charging</CardTitle>
              <Battery className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.charging}</div>
              <p className="text-xs text-muted-foreground">
                Recharging
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Tasks Completed</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_tasks_completed}</div>
              <p className="text-xs text-muted-foreground">
                All-time completions
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Average Battery Level */}
      {stats && stats.average_battery_level !== undefined && (
        <Alert>
          <Battery className="h-4 w-4" />
          <AlertDescription>
            Fleet average battery level: {stats.average_battery_level.toFixed(1)}%
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content */}
      <Tabs defaultValue="robots" className="space-y-4">
        <TabsList>
          <TabsTrigger value="robots">
            <Cpu className="h-4 w-4 mr-2" />
            Robots
          </TabsTrigger>
          <TabsTrigger value="zones">
            <Grid3x3 className="h-4 w-4 mr-2" />
            Zones
          </TabsTrigger>
          <TabsTrigger value="assign">
            <Send className="h-4 w-4 mr-2" />
            Assign Task
          </TabsTrigger>
          <TabsTrigger value="register">
            <Plus className="h-4 w-4 mr-2" />
            Register Robot
          </TabsTrigger>
        </TabsList>

        <TabsContent value="robots">
          <RobotsList robots={robots || []} />
        </TabsContent>

        <TabsContent value="zones">
          <ZonesList zones={zones || []} />
        </TabsContent>

        <TabsContent value="assign">
          <AssignTaskForm />
        </TabsContent>

        <TabsContent value="register">
          <RegisterRobotForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// Robots List Component
// ============================================================================

function RobotsList({ robots }: { robots: Robot[] }) {
  const deregisterMutation = useDeregisterRobot();
  const updateMutation = useUpdateRobot();

  const handleDeregister = (id: string) => {
    if (confirm('Are you sure you want to deregister this robot?')) {
      deregisterMutation.mutate(id);
    }
  };

  const getStatusColor = (status: RobotStatus) => {
    switch (status) {
      case 'active':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'idle':
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
      case 'charging':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'maintenance':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'error':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
    }
  };

  const getBatteryColor = (level?: number) => {
    if (!level) return 'text-gray-500';
    if (level < 20) return 'text-red-500';
    if (level < 50) return 'text-amber-500';
    return 'text-green-500';
  };

  if (robots.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8">
          <Cpu className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No robots registered</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {robots.map((robot) => (
        <Card key={robot.id}>
          <CardContent className="p-6">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold">{robot.name}</h3>
                  <p className="text-xs text-muted-foreground">{robot.id}</p>
                </div>
                <Badge variant="outline" className={getStatusColor(robot.status)}>
                  {robot.status.toUpperCase()}
                </Badge>
              </div>

              {robot.battery_level !== undefined && (
                <div className="flex items-center gap-2">
                  <Battery className={`h-4 w-4 ${getBatteryColor(robot.battery_level)}`} />
                  <div className="flex-1">
                    <div className="flex items-center justify-between text-xs">
                      <span>Battery</span>
                      <span className={getBatteryColor(robot.battery_level)}>
                        {robot.battery_level}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden mt-1">
                      <div
                        className={`h-full ${robot.battery_level < 20 ? 'bg-red-500' : robot.battery_level < 50 ? 'bg-amber-500' : 'bg-green-500'}`}
                        style={{ width: `${robot.battery_level}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {robot.location && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3" />
                  <span>
                    ({robot.location.x.toFixed(1)}, {robot.location.y.toFixed(1)})
                  </span>
                </div>
              )}

              <div className="flex flex-wrap gap-1">
                {robot.capabilities.map((cap) => (
                  <Badge key={cap} variant="secondary" className="text-xs">
                    {cap}
                  </Badge>
                ))}
              </div>

              {robot.tasks_completed !== undefined && (
                <p className="text-xs text-muted-foreground">
                  Tasks completed: {robot.tasks_completed}
                </p>
              )}

              {robot.current_task_id && (
                <Alert>
                  <AlertDescription className="text-xs">
                    Current task: {robot.current_task_id}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                variant="destructive"
                size="sm"
                className="w-full"
                onClick={() => handleDeregister(robot.id)}
                disabled={deregisterMutation.isPending}
              >
                <Trash2 className="h-3 w-3 mr-1" />
                Deregister
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Coordination Zones List Component
// ============================================================================

function ZonesList({ zones }: { zones: any[] }) {
  if (zones.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8">
          <Grid3x3 className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No coordination zones defined</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {zones.map((zone) => (
        <Card key={zone.id}>
          <CardHeader>
            <CardTitle>{zone.name}</CardTitle>
            <CardDescription>Zone ID: {zone.id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Max Robots:</span>
                <span className="ml-2 font-medium">{zone.max_robots}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Current:</span>
                <span className="ml-2 font-medium">{zone.current_robots}</span>
              </div>
            </div>

            {zone.robots && zone.robots.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Active Robots:</p>
                <div className="flex flex-wrap gap-1">
                  {zone.robots.map((robotId: string) => (
                    <Badge key={robotId} variant="secondary" className="text-xs">
                      {robotId}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="text-xs text-muted-foreground">
              Area: ({zone.area.x_min}, {zone.area.y_min}) to ({zone.area.x_max}, {zone.area.y_max})
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Assign Task Form Component
// ============================================================================

function AssignTaskForm() {
  const [taskId, setTaskId] = useState('');
  const [robotId, setRobotId] = useState('');
  const [requirements, setRequirements] = useState('');
  const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'critical'>('normal');
  const assignMutation = useAssignTask();

  const handleAssign = () => {
    if (!taskId.trim()) return;

    const requirementsArray = requirements
      .split(',')
      .map((r) => r.trim())
      .filter((r) => r.length > 0);

    assignMutation.mutate(
      {
        task_id: taskId,
        robot_id: robotId || undefined,
        requirements: requirementsArray.length > 0 ? requirementsArray : undefined,
        priority,
      },
      {
        onSuccess: () => {
          setTaskId('');
          setRobotId('');
          setRequirements('');
          setPriority('normal');
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assign Task to Robot</CardTitle>
        <CardDescription>
          Assign a task to a specific robot or let the system choose optimally
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Task ID</Label>
          <Input
            placeholder="e.g., delivery_001"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label>Robot ID (optional - leave empty for optimal selection)</Label>
          <Input
            placeholder="e.g., robot_001"
            value={robotId}
            onChange={(e) => setRobotId(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label>Requirements (comma-separated, optional)</Label>
          <Input
            placeholder="e.g., navigation, package_delivery"
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label>Priority</Label>
          <div className="flex gap-2">
            {(['low', 'normal', 'high', 'critical'] as const).map((p) => (
              <Badge
                key={p}
                variant={priority === p ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setPriority(p)}
              >
                {p.toUpperCase()}
              </Badge>
            ))}
          </div>
        </div>

        <Button
          onClick={handleAssign}
          disabled={assignMutation.isPending || !taskId.trim()}
          className="w-full"
        >
          {assignMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Assigning Task...
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Assign Task
            </>
          )}
        </Button>

        {assignMutation.isSuccess && assignMutation.data && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>
              Task assigned to robot: {assignMutation.data.robot_id}
              <br />
              <span className="text-xs text-muted-foreground">
                Assignment time: {new Date(assignMutation.data.assignment_time).toLocaleString()}
              </span>
            </AlertDescription>
          </Alert>
        )}

        {assignMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{assignMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Register Robot Form Component
// ============================================================================

function RegisterRobotForm() {
  const [robotId, setRobotId] = useState('');
  const [name, setName] = useState('');
  const [capabilities, setCapabilities] = useState('');
  const [maxPayload, setMaxPayload] = useState(50);
  const [batteryCapacity, setBatteryCapacity] = useState(100);
  const registerMutation = useRegisterRobot();

  const handleRegister = () => {
    if (!robotId.trim() || !name.trim()) return;

    const capsArray = capabilities
      .split(',')
      .map((c) => c.trim())
      .filter((c) => c.length > 0);

    registerMutation.mutate(
      {
        id: robotId,
        name,
        capabilities: capsArray,
        max_payload: maxPayload,
        battery_capacity: batteryCapacity,
      },
      {
        onSuccess: () => {
          setRobotId('');
          setName('');
          setCapabilities('');
          setMaxPayload(50);
          setBatteryCapacity(100);
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Register New Robot</CardTitle>
        <CardDescription>
          Add a new robot to the fleet
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Robot ID</Label>
            <Input
              placeholder="e.g., robot_001"
              value={robotId}
              onChange={(e) => setRobotId(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Robot Name</Label>
            <Input
              placeholder="e.g., Delivery Bot Alpha"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Capabilities (comma-separated)</Label>
          <Input
            placeholder="e.g., navigation, package_delivery, surveillance"
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Max Payload (kg)</Label>
            <Input
              type="number"
              value={maxPayload}
              onChange={(e) => setMaxPayload(parseFloat(e.target.value) || 50)}
            />
          </div>
          <div className="space-y-2">
            <Label>Battery Capacity (%)</Label>
            <Input
              type="number"
              value={batteryCapacity}
              onChange={(e) => setBatteryCapacity(parseFloat(e.target.value) || 100)}
            />
          </div>
        </div>

        <Button
          onClick={handleRegister}
          disabled={registerMutation.isPending || !robotId.trim() || !name.trim()}
          className="w-full"
        >
          {registerMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Registering Robot...
            </>
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Register Robot
            </>
          )}
        </Button>

        {registerMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>Robot registered successfully</AlertDescription>
          </Alert>
        )}

        {registerMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{registerMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

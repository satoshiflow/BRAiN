"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import { useState } from "react";
import { useHardwareInfo, useRobotState, useQuickCommands, useMotorHealth } from "@/hooks/useHardware";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2, Cpu, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, StopCircle, Gauge, Thermometer, Battery, Wifi } from "lucide-react";

export default function HardwarePage() {
  const [selectedRobotId, setSelectedRobotId] = useState<string>("");
  const [robotIdInput, setRobotIdInput] = useState<string>("");

  const { data: info, isLoading: infoLoading } = useHardwareInfo();
  const { data: state, isLoading: stateLoading } = useRobotState(selectedRobotId || undefined);
  const motorHealth = useMotorHealth(selectedRobotId || undefined);
  const commands = useQuickCommands(selectedRobotId);

  const handleViewRobot = () => {
    if (robotIdInput.trim()) {
      setSelectedRobotId(robotIdInput.trim());
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Hardware Control</h2>
          <p className="text-muted-foreground">
            Robot hardware control and real-time state monitoring
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          {info?.version || "v1.0.0"}
        </Badge>
      </div>

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle>Hardware Module</CardTitle>
          <CardDescription>{info?.description || "Robot hardware control system"}</CardDescription>
        </CardHeader>
        <CardContent>
          {infoLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {info?.supported_robots.map((robot) => (
                <Badge key={robot} variant="secondary">
                  {robot}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Robot Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Robot Control</CardTitle>
          <CardDescription>Enter a robot ID to control its hardware</CardDescription>
        </CardHeader>
        <CardContent className="flex items-end gap-4">
          <div className="flex-1 space-y-2">
            <Label htmlFor="robot-id">Robot ID</Label>
            <Input
              id="robot-id"
              placeholder="e.g., robot_001"
              value={robotIdInput}
              onChange={(e) => setRobotIdInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleViewRobot()}
            />
          </div>
          <Button onClick={handleViewRobot} disabled={!robotIdInput.trim()}>
            Connect
          </Button>
        </CardContent>
      </Card>

      {/* Robot State Display */}
      {selectedRobotId && (
        <>
          {stateLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : state ? (
            <div className="space-y-6">
              {/* Movement Controls */}
              <Card>
                <CardHeader>
                  <CardTitle>Movement Control</CardTitle>
                  <CardDescription>Control robot movement direction and speed</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col items-center gap-4">
                    <Button
                      size="lg"
                      variant="outline"
                      onClick={commands.moveForward}
                      disabled={commands.isPending}
                    >
                      <ArrowUp className="h-6 w-6" />
                    </Button>
                    <div className="flex gap-4">
                      <Button
                        size="lg"
                        variant="outline"
                        onClick={commands.turnLeft}
                        disabled={commands.isPending}
                      >
                        <ArrowLeft className="h-6 w-6" />
                      </Button>
                      <Button
                        size="lg"
                        variant="destructive"
                        onClick={commands.stop}
                        disabled={commands.isPending}
                      >
                        <StopCircle className="h-6 w-6" />
                      </Button>
                      <Button
                        size="lg"
                        variant="outline"
                        onClick={commands.turnRight}
                        disabled={commands.isPending}
                      >
                        <ArrowRight className="h-6 w-6" />
                      </Button>
                    </div>
                    <Button
                      size="lg"
                      variant="outline"
                      onClick={commands.moveBackward}
                      disabled={commands.isPending}
                    >
                      <ArrowDown className="h-6 w-6" />
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Motor Status */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <Cpu className="h-4 w-4" />
                      Left Motor
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Power:</span>
                      <span className="font-mono">{(state.motors.left.power * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>RPM:</span>
                      <span className="font-mono">{state.motors.left.rpm}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Temp:</span>
                      <span className={`font-mono ${state.motors.left.temperature > 80 ? "text-destructive" : ""}`}>
                        {state.motors.left.temperature}°C
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <Cpu className="h-4 w-4" />
                      Right Motor
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Power:</span>
                      <span className="font-mono">{(state.motors.right.power * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>RPM:</span>
                      <span className="font-mono">{state.motors.right.rpm}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Temp:</span>
                      <span className={`font-mono ${state.motors.right.temperature > 80 ? "text-destructive" : ""}`}>
                        {state.motors.right.temperature}°C
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* System Status */}
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Battery</CardTitle>
                    <Battery className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{state.battery.percentage.toFixed(0)}%</div>
                    <p className="text-xs text-muted-foreground">
                      {state.battery.voltage.toFixed(2)}V / {state.battery.current.toFixed(2)}A
                    </p>
                    {state.battery.charging && (
                      <Badge variant="default" className="mt-2">
                        Charging
                      </Badge>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">WiFi</CardTitle>
                    <Wifi className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{state.connectivity.wifi_strength}%</div>
                    <p className="text-xs text-muted-foreground">
                      {state.connectivity.latency_ms.toFixed(0)}ms latency
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Health</CardTitle>
                    <Thermometer className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {motorHealth?.isHealthy ? "✅" : "⚠️"}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {motorHealth?.isHealthy ? "All systems OK" : "Check motors"}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Sensors */}
              {state.sensors && (
                <Card>
                  <CardHeader>
                    <CardTitle>Sensors</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {state.sensors.ultrasonic && (
                      <div className="rounded-lg border p-3">
                        <p className="mb-1 text-sm font-medium">Ultrasonic</p>
                        <p className="text-sm text-muted-foreground">
                          Distance: {state.sensors.ultrasonic.distance_cm}cm
                          {!state.sensors.ultrasonic.reliable && " (unreliable)"}
                        </p>
                      </div>
                    )}
                    {state.sensors.imu && (
                      <div className="rounded-lg border p-3">
                        <p className="mb-1 text-sm font-medium">IMU Orientation</p>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <span className="text-muted-foreground">Roll:</span>{" "}
                            {state.sensors.imu.orientation.roll.toFixed(1)}°
                          </div>
                          <div>
                            <span className="text-muted-foreground">Pitch:</span>{" "}
                            {state.sensors.imu.orientation.pitch.toFixed(1)}°
                          </div>
                          <div>
                            <span className="text-muted-foreground">Yaw:</span>{" "}
                            {state.sensors.imu.orientation.yaw.toFixed(1)}°
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

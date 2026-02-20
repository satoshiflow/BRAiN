"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { useState } from "react";
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { useTelemetryInfo, useRobotMetrics, useIsRobotHealthy } from "@/hooks/useTelemetry";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Loader2, Activity, Zap, Thermometer, Cpu, Battery, MapPin } from "lucide-react";

export default function TelemetryPage() {
  const [selectedRobotId, setSelectedRobotId] = useState<string>("");
  const [robotIdInput, setRobotIdInput] = useState<string>("");

  const { data: info, isLoading: infoLoading } = useTelemetryInfo();
  
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useRobotMetrics(selectedRobotId || undefined);
  
  const isHealthy = useIsRobotHealthy(selectedRobotId || undefined);

  const handleLoadMetrics = () => {
  // Show loading skeleton
  if (infoLoading || metricsLoading) {
    return <PageSkeleton variant="dashboard" />;
  }
    if (robotIdInput.trim()) {
      setSelectedRobotId(robotIdInput.trim());
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Telemetry</h2>
          <p className="text-muted-foreground">
            Real-time robot metrics and monitoring
          </p>
        </div>
        {info && (
          <Badge variant="outline" className="text-sm">
            {info.active_websockets} Active Connections
          </Badge>
        )}
      </div>

      {/* System Info */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {infoLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{info?.name || "Telemetry"}</div>
                <p className="text-xs text-muted-foreground">Version {info?.version || "1.0.0"}</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Robots Monitored</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{info?.total_robots_monitored || 0}</div>
            <p className="text-xs text-muted-foreground">Total robots</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">WebSocket</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{info?.active_websockets || 0}</div>
            <p className="text-xs text-muted-foreground">Active connections</p>
          </CardContent>
        </Card>
      </div>

      {/* Robot Metrics Viewer */}
      <Card>
        <CardHeader>
          <CardTitle>Robot Metrics</CardTitle>
          <CardDescription>
            Enter a robot ID to view real-time telemetry data
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Robot ID Input */}
          <div className="flex items-end gap-4">
            <div className="flex-1 space-y-2">
              <Label htmlFor="robot-id">Robot ID</Label>
              <Input
                id="robot-id"
                placeholder="e.g., robot_001"
                value={robotIdInput}
                onChange={(e) => setRobotIdInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLoadMetrics()}
              />
            </div>
            <Button onClick={handleLoadMetrics} disabled={!robotIdInput.trim()}>
              Load Metrics
            </Button>
          </div>

          {/* Metrics Display */}
          {selectedRobotId && (
            <>
              {metricsLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              )}

              {metricsError && (
                <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
                  Error loading metrics: {metricsError.message}
                </div>
              )}

              {metrics && (
                <div className="space-y-4">
                  {/* Status Badge */}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Status:</span>
                      <Badge variant={isHealthy ? "default" : "destructive"}>
                        {metrics.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Last update: {new Date(metrics.timestamp).toLocaleString()}
                    </div>
                  </div>

                  {/* Metrics Grid */}
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {/* CPU Usage */}
                    {metrics.cpu_usage !== undefined && (
                      <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                          <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
                          <Cpu className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold">{metrics.cpu_usage.toFixed(1)}%</div>
                          <div className="mt-2 h-2 rounded-full bg-secondary">
                            <div
                              className="h-2 rounded-full bg-primary transition-all"
                              style={{ width: `${metrics.cpu_usage}%` }}
                            />
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* Memory Usage */}
                    {metrics.memory_usage !== undefined && (
                      <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                          <CardTitle className="text-sm font-medium">Memory</CardTitle>
                          <Activity className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold">{metrics.memory_usage.toFixed(1)}%</div>
                          <div className="mt-2 h-2 rounded-full bg-secondary">
                            <div
                              className="h-2 rounded-full bg-primary transition-all"
                              style={{ width: `${metrics.memory_usage}%` }}
                            />
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* Battery Level */}
                    {metrics.battery_level !== undefined && (
                      <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                          <CardTitle className="text-sm font-medium">Battery</CardTitle>
                          <Battery className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold">{metrics.battery_level.toFixed(1)}%</div>
                          <div className="mt-2 h-2 rounded-full bg-secondary">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                metrics.battery_level < 20
                                  ? "bg-destructive"
                                  : metrics.battery_level < 50
                                  ? "bg-yellow-500"
                                  : "bg-green-500"
                              }`}
                              style={{ width: `${metrics.battery_level}%` }}
                            />
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* Temperature */}
                    {metrics.temperature !== undefined && (
                      <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                          <CardTitle className="text-sm font-medium">Temperature</CardTitle>
                          <Thermometer className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold">{metrics.temperature.toFixed(1)}°C</div>
                          <p className="text-xs text-muted-foreground">
                            {metrics.temperature > 80 ? "⚠️ High" : metrics.temperature > 60 ? "Normal" : "Cool"}
                          </p>
                        </CardContent>
                      </Card>
                    )}
                  </div>

                  {/* Position & Velocity */}
                  {(metrics.position || metrics.velocity) && (
                    <div className="grid gap-4 md:grid-cols-2">
                      {/* Position */}
                      {metrics.position && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-sm font-medium">
                              <MapPin className="h-4 w-4" />
                              Position
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">X:</span>
                                <span className="font-mono">{metrics.position.x.toFixed(2)}m</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Y:</span>
                                <span className="font-mono">{metrics.position.y.toFixed(2)}m</span>
                              </div>
                              {metrics.position.z !== undefined && (
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Z:</span>
                                  <span className="font-mono">{metrics.position.z.toFixed(2)}m</span>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Velocity */}
                      {metrics.velocity && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-sm font-medium">
                              <Zap className="h-4 w-4" />
                              Velocity
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">X:</span>
                                <span className="font-mono">{metrics.velocity.x.toFixed(2)}m/s</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Y:</span>
                                <span className="font-mono">{metrics.velocity.y.toFixed(2)}m/s</span>
                              </div>
                              {metrics.velocity.z !== undefined && (
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Z:</span>
                                  <span className="font-mono">{metrics.velocity.z.toFixed(2)}m/s</span>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  )}

                  {/* Custom Metrics */}
                  {metrics.custom_metrics && Object.keys(metrics.custom_metrics).length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm font-medium">Custom Metrics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1 text-sm">
                          {Object.entries(metrics.custom_metrics).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-muted-foreground">{key}:</span>
                              <span className="font-mono">{JSON.stringify(value)}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

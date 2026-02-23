"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card";
import { Badge } from "@ui-core/components/badge";
import { Button } from "@ui-core/components/button";
import { Alert, AlertDescription } from "@ui-core/components/alert";
import { 
  Activity, 
  Server, 
  Database, 
  Cpu,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
  TrendingUp,
  Activity as Pulse
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de";

interface HealthService {
  id: string;
  service_name: string;
  service_type: string;
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  last_check_at: string | null;
  response_time_ms: number | null;
  uptime_percentage: number | null;
  consecutive_failures: number;
  error_message: string | null;
}

interface HealthSummary {
  overall_status: "healthy" | "degraded" | "unhealthy" | "unknown";
  total_services: number;
  healthy_count: number;
  degraded_count: number;
  unhealthy_count: number;
  unknown_count: number;
  services: HealthService[];
}

export default function HealthPage() {
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health/status`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.error("Failed to fetch health status");
    } finally {
      setLoading(false);
    }
  };

  const refreshHealth = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/api/health/check`, { method: "POST" });
      await fetchHealth();
    } catch (e) {
      setError("Failed to refresh health checks");
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "degraded":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case "unhealthy":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "degraded":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      case "unhealthy":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      default:
        return "bg-gray-500/10 text-gray-400 border-gray-500/20";
    }
  };

  const getServiceIcon = (type: string) => {
    switch (type) {
      case "database":
        return <Database className="h-4 w-4" />;
      case "cache":
        return <Cpu className="h-4 w-4" />;
      case "external":
        return <Server className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <DashboardLayout title="Health Monitor" subtitle="System health and monitoring">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout 
      title="Health Monitor" 
      subtitle="Real-time system health monitoring"
    >
      <div className="space-y-6">
        {/* Overall Status */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className={cn("border-l-4", getStatusColor(health?.overall_status || "unknown"))}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Overall Status</p>
                  <p className="text-2xl font-bold capitalize">{health?.overall_status || "Unknown"}</p>
                </div>
                {getStatusIcon(health?.overall_status || "unknown")}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Healthy Services</p>
                  <p className="text-2xl font-bold text-green-500">{health?.healthy_count || 0}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Degraded</p>
                  <p className="text-2xl font-bold text-yellow-500">{health?.degraded_count || 0}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Unhealthy</p>
                  <p className="text-2xl font-bold text-red-500">{health?.unhealthy_count || 0}</p>
                </div>
                <XCircle className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex justify-end">
          <Button onClick={refreshHealth} disabled={refreshing}>
            <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
            {refreshing ? "Checking..." : "Run Health Check"}
          </Button>
        </div>

        {error && (
          <Alert className="bg-red-500/10 border-red-500/20">
            <AlertDescription className="text-red-600">{error}</AlertDescription>
          </Alert>
        )}

        {/* Services Grid */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Pulse className="h-5 w-5" />
              Monitored Services
            </CardTitle>
            <CardDescription>
              {health?.total_services || 0} services under monitoring
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {health?.services.map((service) => (
                <Card key={service.id} className={cn("border-l-4", getStatusColor(service.status))}>
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        {getServiceIcon(service.service_type)}
                        <span className="font-medium">{service.service_name}</span>
                      </div>
                      <Badge variant="outline" className={cn("text-xs", getStatusColor(service.status))}>
                        {service.status}
                      </Badge>
                    </div>
                    
                    <div className="mt-3 space-y-1 text-sm">
                      {service.response_time_ms && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <TrendingUp className="h-3 w-3" />
                          <span>{Math.round(service.response_time_ms)}ms response</span>
                        </div>
                      )}
                      {service.uptime_percentage && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Activity className="h-3 w-3" />
                          <span>{service.uptime_percentage.toFixed(1)}% uptime</span>
                        </div>
                      )}
                      {service.last_check_at && (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>Checked {new Date(service.last_check_at).toLocaleTimeString()}</span>
                        </div>
                      )}
                    </div>

                    {service.error_message && (
                      <div className="mt-2 p-2 bg-red-500/10 rounded text-xs text-red-600">
                        {service.error_message}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
            
            {(!health?.services || health.services.length === 0) && (
              <div className="text-center py-12 text-muted-foreground">
                <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No services registered for health monitoring</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

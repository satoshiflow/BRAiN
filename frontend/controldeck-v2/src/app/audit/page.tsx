"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card";
import { Badge } from "@ui-core/components/badge";
import { Input, Label } from "@ui-core/components/input";
import { Alert, AlertDescription } from "@ui-core/components/alert";
import { 
  Shield,
  RefreshCw,
  User,
  Calendar,
  Filter,
  AlertCircle,
  CheckCircle,
  Info,
  FileText,
  Eye,
  Edit,
  Trash2,
  Plus
} from "lucide-react";
// Date formatting helper
function formatDate(dateStr: string) {
  return new Intl.DateTimeFormat('en-US', { 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  }).format(new Date(dateStr));
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de";

interface AuditEvent {
  id: string;
  event_type: string;
  action: string;
  actor: string;
  actor_type: string;
  resource_type?: string;
  resource_id?: string;
  severity: "info" | "warning" | "error" | "critical";
  message?: string;
  created_at: string;
  ip_address?: string;
}

interface AuditStats {
  total_events: number;
  by_type: Record<string, number>;
  by_action: Record<string, number>;
  by_severity: Record<string, number>;
}

// Simple Bar Chart Component
function SimpleBarChart({ data, maxValue }: { data: { label: string; value: number; color: string }[]; maxValue: number }) {
  return (
    <div className="space-y-2">
      {data.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="text-xs w-20 truncate">{item.label}</span>
          <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-500"
              style={{ 
                width: `${(item.value / maxValue) * 100}%`,
                backgroundColor: item.color 
              }}
            />
          </div>
          <span className="text-xs w-8 text-right">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    event_type: "",
    action: "",
    actor: "",
    severity: "",
  });

  useEffect(() => {
    fetchEvents();
    fetchStats();
  }, []);

  const fetchEvents = async () => {
    try {
      const params = new URLSearchParams();
      if (filter.event_type) params.append("event_type", filter.event_type);
      if (filter.action) params.append("action", filter.action);
      if (filter.actor) params.append("actor", filter.actor);
      if (filter.severity) params.append("severity", filter.severity);

      const res = await fetch(`${API_BASE}/api/audit/events?${params}&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch audit events");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/audit/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch stats");
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case "warning":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-500/10 text-red-500";
      case "error":
        return "bg-orange-500/10 text-orange-500";
      case "warning":
        return "bg-yellow-500/10 text-yellow-500";
      default:
        return "bg-blue-500/10 text-blue-500";
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case "create":
        return <Plus className="h-4 w-4 text-green-500" />;
      case "update":
        return <Edit className="h-4 w-4 text-blue-500" />;
      case "delete":
        return <Trash2 className="h-4 w-4 text-red-500" />;
      default:
        return <Eye className="h-4 w-4 text-gray-500" />;
    }
  };

  // Prepare chart data
  const typeChartData = stats?.by_type 
    ? Object.entries(stats.by_type).map(([key, value]) => ({ 
        label: key, 
        value, 
        color: "#3b82f6" 
      }))
    : [];

  const actionChartData = stats?.by_action 
    ? Object.entries(stats.by_action).map(([key, value]) => ({ 
        label: key, 
        value, 
        color: "#10b981" 
      }))
    : [];

  const maxTypeValue = Math.max(...typeChartData.map(d => d.value), 1);
  const maxActionValue = Math.max(...actionChartData.map(d => d.value), 1);

  return (
    <DashboardLayout title="Audit Log" subtitle="Track all system activities">
      <div className="space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Events</p>
                  <p className="text-2xl font-bold">{stats?.total_events || 0}</p>
                </div>
                <Shield className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Critical</p>
                  <p className="text-2xl font-bold text-red-500">
                    {stats?.by_severity?.critical || 0}
                  </p>
                </div>
                <AlertCircle className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Operations</p>
                  <p className="text-2xl font-bold text-blue-500">
                    {stats?.by_type?.operation || 0}
                  </p>
                </div>
                <FileText className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Security Events</p>
                  <p className="text-2xl font-bold text-orange-500">
                    {stats?.by_type?.security || 0}
                  </p>
                </div>
                <User className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Events by Type</CardTitle>
            </CardHeader>
            <CardContent>
              {typeChartData.length > 0 ? (
                <SimpleBarChart data={typeChartData} maxValue={maxTypeValue} />
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No data</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Events by Action</CardTitle>
            </CardHeader>
            <CardContent>
              {actionChartData.length > 0 ? (
                <SimpleBarChart data={actionChartData} maxValue={maxActionValue} />
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No data</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <select
                  value={filter.event_type}
                  onChange={(e) => setFilter({...filter, event_type: e.target.value})}
                  className="h-9 px-3 rounded-md border border-input bg-background text-sm"
                >
                  <option value="">All Types</option>
                  <option value="operation">Operation</option>
                  <option value="security">Security</option>
                  <option value="system">System</option>
                </select>
              </div>
              <select
                value={filter.action}
                onChange={(e) => setFilter({...filter, action: e.target.value})}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="">All Actions</option>
                <option value="create">Create</option>
                <option value="update">Update</option>
                <option value="delete">Delete</option>
                <option value="login">Login</option>
              </select>
              <select
                value={filter.severity}
                onChange={(e) => setFilter({...filter, severity: e.target.value})}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm"
              >
                <option value="">All Severities</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="critical">Critical</option>
              </select>
              <Input
                placeholder="Filter by actor..."
                value={filter.actor}
                onChange={(e) => setFilter({...filter, actor: e.target.value})}
                className="w-40 h-9"
              />
              <Button size="sm" onClick={fetchEvents}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Apply
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Events List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Recent Events
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : events.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No audit events found</p>
              </div>
            ) : (
              <div className="space-y-2">
                {events.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center gap-4 p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex-shrink-0">
                      {getSeverityIcon(event.severity)}
                    </div>
                    
                    <div className="flex-shrink-0">
                      {getActionIcon(event.action)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{event.action}</span>
                        {event.resource_type && (
                          <>
                            <span className="text-muted-foreground">on</span>
                            <span className="text-sm">{event.resource_type}</span>
                          </>
                        )}
                        <Badge variant="outline" className={getSeverityColor(event.severity)}>
                          {event.severity}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {event.actor}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {formatDate(event.created_at)}
                        </span>
                        {event.ip_address && (
                          <span>from {event.ip_address}</span>
                        )}
                      </div>
                      {event.message && (
                        <p className="text-sm text-muted-foreground mt-1">{event.message}</p>
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

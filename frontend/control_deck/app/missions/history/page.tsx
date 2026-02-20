"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useState, useEffect } from "react";
import {
  History,
  Search,
  Filter,
  Download,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface MissionHistory {
  id: string;
  name: string;
  status: "COMPLETED" | "FAILED" | "CANCELLED" | "RUNNING" | "PENDING";
  created_at: string;
  completed_at?: string;
  duration_ms?: number;
  agent_type?: string;
  result?: any;
  error?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://127.0.0.1:8001";

export default function MissionHistoryPage() {
  const [missions, setMissions] = useState<MissionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    fetchHistory();
  }, []);

  async function fetchHistory() {
    try {
      const response = await fetch(`${API_BASE}/api/missions/events/history`);
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data)) {
          setMissions(data);
        } else {
          // Use mock data if API doesn't return array
          setMockData();
        }
      } else {
        setMockData();
      }
    } catch (error) {
      console.error("Failed to fetch mission history:", error);
      setMockData();
    } finally {
      setLoading(false);
    }
  }

  function setMockData() {
    setMissions([
      {
        id: "mission-001",
        name: "System Health Check",
        status: "COMPLETED",
        created_at: new Date(Date.now() - 3600000).toISOString(),
        completed_at: new Date(Date.now() - 3500000).toISOString(),
        duration_ms: 100000,
        agent_type: "system",
      },
      {
        id: "mission-002",
        name: "Data Processing Task",
        status: "COMPLETED",
        created_at: new Date(Date.now() - 7200000).toISOString(),
        completed_at: new Date(Date.now() - 7000000).toISOString(),
        duration_ms: 200000,
        agent_type: "worker",
      },
      {
        id: "mission-003",
        name: "Failed Backup",
        status: "FAILED",
        created_at: new Date(Date.now() - 10800000).toISOString(),
        completed_at: new Date(Date.now() - 10750000).toISOString(),
        duration_ms: 50000,
        agent_type: "backup",
        error: "Connection timeout",
      },
    ]);
  }

  const filteredMissions = missions.filter((m) => {
    const matchesSearch = m.name.toLowerCase().includes(search.toLowerCase()) ||
                         m.id.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || m.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (loading) return <PageSkeleton />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Mission History</h1>
          <p className="text-sm text-muted-foreground">
            Complete log of all executed missions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchHistory}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Past Missions ({filteredMissions.length})
            </CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search missions..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 w-[200px]"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-sm border rounded px-2 py-2 bg-background"
              >
                <option value="all">All Status</option>
                <option value="COMPLETED">Completed</option>
                <option value="FAILED">Failed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium">Mission</th>
                  <th className="text-left py-3 px-4 font-medium">Status</th>
                  <th className="text-left py-3 px-4 font-medium">Created</th>
                  <th className="text-left py-3 px-4 font-medium">Duration</th>
                  <th className="text-left py-3 px-4 font-medium">Agent</th>
                </tr>
              </thead>
              <tbody>
                {filteredMissions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">
                      No missions found
                    </td>
                  </tr>
                ) : (
                  filteredMissions.map((mission) => (
                    <tr key={mission.id} className="border-b hover:bg-secondary/50">
                      <td className="py-3 px-4">
                        <div>
                          <div className="font-medium">{mission.name}</div>
                          <div className="text-xs text-muted-foreground">{mission.id}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={mission.status} />
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {new Date(mission.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {mission.duration_ms 
                          ? `${(mission.duration_ms / 1000).toFixed(1)}s`
                          : "-"
                        }
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline">{mission.agent_type || "unknown"}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { icon: React.ReactNode; className: string }> = {
    COMPLETED: {
      icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
      className: "bg-green-500/10 text-green-500 border-green-500/20",
    },
    FAILED: {
      icon: <XCircle className="h-3 w-3 mr-1" />,
      className: "bg-red-500/10 text-red-500 border-red-500/20",
    },
    CANCELLED: {
      icon: <AlertCircle className="h-3 w-3 mr-1" />,
      className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    },
    RUNNING: {
      icon: <Clock className="h-3 w-3 mr-1" />,
      className: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    },
    PENDING: {
      icon: <Clock className="h-3 w-3 mr-1" />,
      className: "bg-gray-500/10 text-gray-500 border-gray-500/20",
    },
  };

  const variant = variants[status] || variants.PENDING;

  return (
    <Badge variant="outline" className={`flex items-center w-fit ${variant.className}`}>
      {variant.icon}
      {status}
    </Badge>
  );
}

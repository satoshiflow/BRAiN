"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  ArrowLeft, 
  Plus, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Code,
  Filter,
  RefreshCw
} from "lucide-react";

interface Ticket {
  id: string;
  ticket_id: string;
  type: string;
  severity: "S1" | "S2" | "S3" | "S4";
  component: string;
  summary: string;
  status: string;
  created_at: string;
}

export default function FredBridgePage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    open: 0,
    inProgress: 0,
    patchesPending: 0,
  });

  useEffect(() => {
    fetchTickets();
    const interval = setInterval(fetchTickets, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await fetch("/api/fred-bridge/tickets?limit=100");
      if (response.ok) {
        const data = await response.json();
        setTickets(data.tickets || []);
        
        // Calculate stats
        const open = data.tickets?.filter((t: Ticket) => t.status === "open").length || 0;
        const inProgress = data.tickets?.filter((t: Ticket) => 
          ["in_analysis", "patch_submitted"].includes(t.status)
        ).length || 0;
        
        setStats({ open, inProgress, patchesPending: 0 });
      }
    } catch (error) {
      console.error("Failed to fetch tickets:", error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "S1": return "bg-red-500";
      case "S2": return "bg-orange-500";
      case "S3": return "bg-yellow-500";
      case "S4": return "bg-blue-500";
      default: return "bg-gray-500";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "open": return <AlertTriangle className="h-4 w-4 text-yellow-400" />;
      case "accepted": return <CheckCircle className="h-4 w-4 text-green-400" />;
      default: return <Clock className="h-4 w-4 text-blue-400" />;
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Fred Bridge</h1>
            <p className="text-sm text-muted-foreground">
              Development Intelligence Interface
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchTickets}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={() => router.push("/fred-bridge/tickets/new")}>
            <Plus className="h-4 w-4 mr-2" />
            New Ticket
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Open Tickets
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.open}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Waiting for analysis
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              In Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.inProgress}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Analysis or patch submitted
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Patches Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.patchesPending}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Awaiting approval
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tickets List */}
      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Tickets</CardTitle>
              <CardDescription>
                Development requests and incidents
              </CardDescription>
            </div>
            <Button variant="outline" size="sm">
              <Filter className="h-4 w-4 mr-2" />
              Filter
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No tickets yet. Create one to get started.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className="flex items-center gap-4 p-4 rounded-lg border border-border/50 hover:bg-secondary/50 cursor-pointer transition-colors"
                  onClick={() => router.push(`/fred-bridge/tickets/${ticket.ticket_id}`)}
                >
                  {/* Severity Badge */}
                  <div className={`w-3 h-3 rounded-full ${getSeverityColor(ticket.severity)}`} />
                  
                  {/* Status Icon */}
                  {getStatusIcon(ticket.status)}
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground">
                        {ticket.ticket_id}
                      </span>
                      <Badge variant="secondary" className="text-xs">
                        {ticket.type}
                      </Badge>
                    </div>
                    <p className="font-medium truncate">{ticket.summary}</p>
                    <p className="text-xs text-muted-foreground">
                      {ticket.component} • {new Date(ticket.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  
                  {/* Status Badge */}
                  <Badge variant="outline" className="capitalize">
                    {ticket.status.replace("_", " ")}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              Mock Fred
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Generate synthetic patches for testing without real Fred running.
            </p>
            <Button variant="outline" onClick={() => router.push("/fred-bridge/mock")}>
              Create Mock Patch
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Pending Approvals
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Review and approve patch artifacts waiting for deployment.
            </p>
            <Button variant="outline" onClick={() => router.push("/fred-bridge/patches")}>
              View Patches
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

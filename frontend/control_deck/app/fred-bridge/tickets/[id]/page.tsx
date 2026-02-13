"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  ArrowLeft, 
  AlertTriangle, 
  Clock, 
  Code, 
  CheckCircle,
  RefreshCw,
  Play
} from "lucide-react";

interface Ticket {
  id: string;
  ticket_id: string;
  type: string;
  severity: string;
  component: string;
  summary: string;
  status: string;
  environment: string;
  reporter: string;
  expected_outcome: string;
  reproduction_steps: string[];
  created_at: string;
  updated_at: string;
}

interface Patch {
  id: string;
  patch_id: string;
  status: string;
  author: string;
  risk_assessment: {
    risk_level: string;
    blast_radius: string;
  };
  created_at: string;
}

export default function TicketDetailPage() {
  const router = useRouter();
  const params = useParams();
  const ticketId = params.id as string;
  
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [patches, setPatches] = useState<Patch[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingMock, setCreatingMock] = useState(false);

  useEffect(() => {
    fetchTicket();
  }, [ticketId]);

  const fetchTicket = async () => {
    try {
      const [ticketRes, patchesRes] = await Promise.all([
        fetch(`/api/fred-bridge/tickets/${ticketId}`),
        fetch(`/api/fred-bridge/patches?ticket_id=${ticketId}`),
      ]);

      if (ticketRes.ok) {
        setTicket(await ticketRes.json());
      }
      if (patchesRes.ok) {
        const data = await patchesRes.json();
        setPatches(data.patches || []);
      }
    } catch (error) {
      console.error("Failed to fetch ticket:", error);
    } finally {
      setLoading(false);
    }
  };

  const createMockPatch = async () => {
    setCreatingMock(true);
    try {
      const response = await fetch("/api/fred-bridge/mock/create-patch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_id: ticketId }),
      });

      if (response.ok) {
        fetchTicket(); // Refresh to show new patch
      }
    } catch (error) {
      console.error("Failed to create mock patch:", error);
    } finally {
      setCreatingMock(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="p-6">
        <Button variant="outline" onClick={() => router.push("/fred-bridge")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Tickets
        </Button>
        <p className="mt-4 text-muted-foreground">Ticket not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => router.push("/fred-bridge")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-muted-foreground">{ticket.ticket_id}</span>
              <div className={`w-2 h-2 rounded-full ${getSeverityColor(ticket.severity)}`} />
              <Badge variant="secondary">{ticket.type}</Badge>
            </div>
            <h1 className="text-2xl font-bold">{ticket.summary}</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={fetchTicket}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={createMockPatch} disabled={creatingMock}>
            <Play className="h-4 w-4 mr-2" />
            {creatingMock ? "Creating..." : "Mock Patch"}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="patches">
            Patches ({patches.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Status Card */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="capitalize font-medium">{ticket.status.replace("_", " ")}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Created {new Date(ticket.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant="outline">{ticket.environment}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Component</CardTitle>
              </CardHeader>
              <CardContent>
                <code className="text-sm">{ticket.component}</code>
              </CardContent>
            </Card>

            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Reporter</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{ticket.reporter}</p>
              </CardContent>
            </Card>
          </div>

          {/* Expected Outcome */}
          {ticket.expected_outcome && (
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Expected Outcome</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{ticket.expected_outcome}</p>
              </CardContent>
            </Card>
          )}

          {/* Reproduction Steps */}
          {ticket.reproduction_steps?.length > 0 && (
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Reproduction Steps</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="list-decimal list-inside space-y-1">
                  {ticket.reproduction_steps.map((step, i) => (
                    <li key={i} className="text-sm">{step}</li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="patches" className="space-y-4">
          {patches.length === 0 ? (
            <Card className="border-border/50">
              <CardContent className="py-8 text-center text-muted-foreground">
                <Code className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No patches yet. Use "Mock Patch" to create a test patch.</p>
              </CardContent>
            </Card>
          ) : (
            patches.map((patch) => (
              <Card key={patch.id} className="border-border/50">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm">{patch.patch_id}</span>
                        <Badge 
                          variant={patch.status === "proposed" ? "secondary" : "default"}
                        >
                          {patch.status}
                        </Badge>
                      </div>
                      <CardDescription>
                        by {patch.author} • {new Date(patch.created_at).toLocaleDateString()}
                      </CardDescription>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => router.push(`/fred-bridge/patches/${patch.patch_id}`)}
                    >
                      View
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Risk: {patch.risk_assessment?.risk_level || "unknown"}
                    </div>
                    <div className="flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      Blast: {patch.risk_assessment?.blast_radius || "unknown"}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

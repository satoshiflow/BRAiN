"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, AlertTriangle, Save } from "lucide-react";

export default function NewTicketPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    type: "incident",
    severity: "S4",
    component: "",
    summary: "",
    expected_outcome: "",
    reproduction_steps: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch("/api/fred-bridge/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          observed_symptoms: { metrics: [], logs: [], traces: [] },
          recent_changes: { commits: [], config_changes: [], runtime_changes: [] },
          constraints: {
            time_budget_minutes: 120,
            max_blast_radius: "single module",
            allowed_actions: ["patch_artifact_only", "tests_required"],
          },
          reproduction_steps: formData.reproduction_steps.split("\n").filter(Boolean),
        }),
      });

      if (response.ok) {
        const ticket = await response.json();
        router.push(`/fred-bridge/tickets/${ticket.ticket_id}`);
      }
    } catch (error) {
      console.error("Failed to create ticket:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="icon" onClick={() => router.push("/fred-bridge")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">New Ticket</h1>
          <p className="text-sm text-muted-foreground">
            Request development intelligence from Fred
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Basic Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) => setFormData({ ...formData, type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="incident">Incident</SelectItem>
                    <SelectItem value="feature">Feature</SelectItem>
                    <SelectItem value="refactor">Refactor</SelectItem>
                    <SelectItem value="security">Security</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Severity</Label>
                <Select
                  value={formData.severity}
                  onValueChange={(value) => setFormData({ ...formData, severity: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="S1">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                        S1 - Critical
                      </div>
                    </SelectItem>
                    <SelectItem value="S2">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-orange-500" />
                        S2 - High
                      </div>
                    </SelectItem>
                    <SelectItem value="S3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-yellow-500" />
                        S3 - Medium
                      </div>
                    </SelectItem>
                    <SelectItem value="S4">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                        S4 - Low
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Component</Label>
              <Input
                placeholder="e.g., mission_system/runner"
                value={formData.component}
                onChange={(e) => setFormData({ ...formData, component: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label>Summary</Label>
              <Input
                placeholder="Short, actionable summary of the issue or request"
                value={formData.summary}
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                required
              />
            </div>
          </CardContent>
        </Card>

        {/* Details */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Expected Outcome</Label>
              <Textarea
                placeholder="What should happen after the fix?"
                value={formData.expected_outcome}
                onChange={(e) => setFormData({ ...formData, expected_outcome: e.target.value })}
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label>Reproduction Steps</Label>
              <Textarea
                placeholder="1. Step one&#10;2. Step two&#10;3. Step three"
                value={formData.reproduction_steps}
                onChange={(e) => setFormData({ ...formData, reproduction_steps: e.target.value })}
                rows={4}
              />
              <p className="text-xs text-muted-foreground">
                One step per line
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => router.push("/fred-bridge")}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>Creating...</>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Create Ticket
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

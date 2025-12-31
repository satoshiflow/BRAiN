"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Shield,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  FileText,
  BarChart3,
  TrendingUp
} from "lucide-react";

// Mock data - replace with actual API calls
const mockAuditTrail = [
  {
    audit_id: "audit_001",
    timestamp: "2023-12-20T14:30:00Z",
    requesting_agent: "CoderAgent",
    action: "generate_odoo_module",
    risk_level: "high",
    approved: false,
    human_oversight_required: true,
    human_oversight_token: "HITL-abc123",
    denial_reason: "HIGH risk: Personal data processing requires human oversight",
    policy_violations: []
  },
  {
    audit_id: "audit_002",
    timestamp: "2023-12-20T14:25:00Z",
    requesting_agent: "OpsAgent",
    action: "deploy_application",
    risk_level: "low",
    approved: true,
    human_oversight_required: false,
    denial_reason: null,
    policy_violations: []
  },
  {
    audit_id: "audit_003",
    timestamp: "2023-12-20T14:20:00Z",
    requesting_agent: "TestAgent",
    action: "deploy_to_production",
    risk_level: "critical",
    approved: false,
    human_oversight_required: true,
    human_oversight_token: "HITL-def456",
    denial_reason: "CRITICAL risk requires human approval",
    policy_violations: ["prod-deploy-senior-only"]
  }
];

const mockMetrics = {
  total_requests: 156,
  approved: 142,
  denied: 14,
  pending_hitl: 3,
  approval_rate: 0.91,
  avg_processing_time: 125
};

const mockPolicyViolations = [
  { rule_id: "prod-deploy-senior-only", count: 5, last_seen: "2023-12-20T14:20:00Z" },
  { rule_id: "personal-data-consent-required", count: 3, last_seen: "2023-12-20T13:45:00Z" },
  { rule_id: "encryption-required", count: 2, last_seen: "2023-12-20T12:30:00Z" }
];

export default function AuditTrailPage() {
  const [timeFilter, setTimeFilter] = useState("24h");
  const [riskFilter, setRiskFilter] = useState("all");

  const getRiskBadge = (level: string) => {
    const colors = {
      low: "bg-green-500/20 text-green-500 border-green-500/50",
      medium: "bg-yellow-500/20 text-yellow-500 border-yellow-500/50",
      high: "bg-orange-500/20 text-orange-500 border-orange-500/50",
      critical: "bg-red-500/20 text-red-500 border-red-500/50"
    };
    return colors[level as keyof typeof colors] || "";
  };

  return (
    <div className="brain-shell">
      <div className="brain-shell-header">
        <div>
          <h1 className="brain-shell-title">Audit Trail & Monitoring</h1>
          <p className="brain-shell-subtitle">
            Comprehensive audit trail for all constitutional agent supervision decisions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeFilter} onValueChange={setTimeFilter}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm">Total Requests</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{mockMetrics.total_requests}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Last {timeFilter}
            </p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-500" />
              Approval Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-500">
              {(mockMetrics.approval_rate * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {mockMetrics.approved} approved / {mockMetrics.denied} denied
            </p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <User className="w-4 h-4 text-yellow-500" />
              Pending HITL
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-500">
              {mockMetrics.pending_hitl}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Awaiting human oversight
            </p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-500" />
              Avg Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-500">
              {mockMetrics.avg_processing_time}ms
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Average response time
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="audit" className="space-y-6">
        <TabsList className="bg-brain-panel border border-white/5">
          <TabsTrigger value="audit" className="data-[state=active]:bg-brain-accent">
            <FileText className="w-4 h-4 mr-2" />
            Audit Trail
          </TabsTrigger>
          <TabsTrigger value="violations" className="data-[state=active]:bg-brain-accent">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Policy Violations
          </TabsTrigger>
          <TabsTrigger value="hitl" className="data-[state=active]:bg-brain-accent">
            <User className="w-4 h-4 mr-2" />
            HITL Queue
          </TabsTrigger>
          <TabsTrigger value="analytics" className="data-[state=active]:bg-brain-accent">
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </TabsTrigger>
        </TabsList>

        {/* Audit Trail Tab */}
        <TabsContent value="audit">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <div className="flex items-center justify-between">
                <CardTitle className="brain-card-title">Supervision Audit Trail</CardTitle>
                <Select value={riskFilter} onValueChange={setRiskFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Filter by risk" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Risk Levels</SelectItem>
                    <SelectItem value="low">LOW</SelectItem>
                    <SelectItem value="medium">MEDIUM</SelectItem>
                    <SelectItem value="high">HIGH</SelectItem>
                    <SelectItem value="critical">CRITICAL</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockAuditTrail.map((entry) => (
                    <TableRow key={entry.audit_id}>
                      <TableCell className="font-mono text-xs">
                        {new Date(entry.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm">
                        {entry.requesting_agent}
                      </TableCell>
                      <TableCell className="text-sm font-medium">
                        {entry.action}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={getRiskBadge(entry.risk_level)}>
                          {entry.risk_level.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {entry.approved ? (
                          <div className="flex items-center gap-2 text-green-500">
                            <CheckCircle2 className="w-4 h-4" />
                            <span className="text-xs">Approved</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-red-500">
                            <XCircle className="w-4 h-4" />
                            <span className="text-xs">Denied</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          {entry.human_oversight_required && (
                            <Badge variant="outline" className="text-xs">
                              <User className="w-3 h-3 mr-1" />
                              HITL: {entry.human_oversight_token}
                            </Badge>
                          )}
                          {entry.policy_violations.length > 0 && (
                            <Badge variant="outline" className="text-xs text-orange-500">
                              <AlertTriangle className="w-3 h-3 mr-1" />
                              {entry.policy_violations.length} violations
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Policy Violations Tab */}
        <TabsContent value="violations">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Policy Violations Summary</CardTitle>
              <CardDescription>Most frequently violated policies</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Policy Rule</TableHead>
                    <TableHead>Violations</TableHead>
                    <TableHead>Last Seen</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockPolicyViolations.map((violation) => (
                    <TableRow key={violation.rule_id}>
                      <TableCell className="font-mono text-sm">
                        {violation.rule_id}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-orange-500">
                          {violation.count} times
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(violation.last_seen).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm">
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* HITL Queue Tab */}
        <TabsContent value="hitl">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Human-in-the-Loop Queue</CardTitle>
              <CardDescription>Pending human oversight approvals</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockAuditTrail
                  .filter((e) => e.human_oversight_required)
                  .map((entry) => (
                    <div
                      key={entry.audit_id}
                      className="border border-white/10 rounded-lg p-4 bg-yellow-500/5"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <Badge className="mb-2 bg-yellow-500/20 text-yellow-500">
                            {entry.human_oversight_token}
                          </Badge>
                          <p className="font-semibold">{entry.action}</p>
                          <p className="text-sm text-muted-foreground">
                            Requested by {entry.requesting_agent}
                          </p>
                        </div>
                        <Badge variant="outline" className={getRiskBadge(entry.risk_level)}>
                          {entry.risk_level.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm mb-3">{entry.denial_reason}</p>
                      <div className="flex gap-2">
                        <Button size="sm" variant="default">
                          Approve
                        </Button>
                        <Button size="sm" variant="destructive">
                          Deny
                        </Button>
                        <Button size="sm" variant="ghost">
                          View Details
                        </Button>
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="brain-card">
              <CardHeader className="brain-card-header">
                <CardTitle className="brain-card-title">Requests by Risk Level</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">LOW</span>
                    <Badge className="bg-green-500/20 text-green-500">120</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">MEDIUM</span>
                    <Badge className="bg-yellow-500/20 text-yellow-500">25</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">HIGH</span>
                    <Badge className="bg-orange-500/20 text-orange-500">8</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">CRITICAL</span>
                    <Badge className="bg-red-500/20 text-red-500">3</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="brain-card">
              <CardHeader className="brain-card-header">
                <CardTitle className="brain-card-title">Most Active Agents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">OpsAgent</span>
                    <Badge variant="outline">85 requests</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">CoderAgent</span>
                    <Badge variant="outline">45 requests</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">ArchitectAgent</span>
                    <Badge variant="outline">18 requests</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">AXEAgent</span>
                    <Badge variant="outline">8 requests</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Compliance Footer */}
      <Card className="brain-card mt-6 border-brain-gold/20">
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-3 text-sm">
            <div>
              <h4 className="font-semibold text-brain-gold mb-2">Audit Retention</h4>
              <p className="text-xs text-muted-foreground">
                All supervision decisions are permanently logged for compliance audits (DSGVO Art. 30)
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-brain-gold mb-2">Human Oversight</h4>
              <p className="text-xs text-muted-foreground">
                HIGH/CRITICAL risk actions require documented human approval (EU AI Act Art. 14, 16)
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-brain-gold mb-2">Data Export</h4>
              <p className="text-xs text-muted-foreground">
                Export audit trail for regulatory reporting and compliance verification
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  FileText,
  TrendingUp,
  ShieldAlert,
} from "lucide-react";
import {
  useHITLQueue,
  useHITLHistory,
  useHITLStats,
  useHITLApprove,
  type HITLApprovalDetails,
  type ApprovalStatus,
} from "@/hooks/useHITL";

/**
 * Human-in-the-Loop Approval Interface
 *
 * Displays pending approval requests and allows authorized users
 * to approve or deny HIGH/CRITICAL risk actions.
 */
export function HITLApprovalInterface() {
  const [selectedApproval, setSelectedApproval] = useState<HITLApprovalDetails | null>(null);
  const [approverName, setApproverName] = useState("");
  const [approvalReason, setApprovalReason] = useState("");
  const [historyStatus, setHistoryStatus] = useState<ApprovalStatus | undefined>(undefined);

  const queue = useHITLQueue();
  const history = useHITLHistory(50, historyStatus);
  const stats = useHITLStats();
  const approveMutation = useHITLApprove();

  const handleApprove = (approval: HITLApprovalDetails, approved: boolean) => {
    if (!approverName.trim()) {
      alert("Please enter your name as approver");
      return;
    }

    approveMutation.mutate(
      {
        token: approval.token,
        approved,
        approved_by: approverName,
        reason: approvalReason || undefined,
      },
      {
        onSuccess: () => {
          setSelectedApproval(null);
          setApprovalReason("");
          alert(`Request ${approved ? "approved" : "denied"} successfully`);
        },
        onError: (error) => {
          alert(`Failed to process request: ${error.message}`);
        },
      }
    );
  };

  return (
    <div className="space-y-6">
      {/* Header with stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <Clock className="w-4 h-4 text-yellow-500" />
              Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.data?.pending ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              Approved
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.data?.approved ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              Denied
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.data?.denied ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-500" />
              Avg Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {stats.data?.avg_approval_time_seconds
                ? `${Math.round(stats.data.avg_approval_time_seconds)}s`
                : "N/A"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Approver Name Input */}
      <Card className="brain-card border-brain-gold/20">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title flex items-center gap-2">
            <User className="w-5 h-5 text-brain-gold" />
            Approver Identity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <Label htmlFor="approver-name">Your Name / ID</Label>
              <Input
                id="approver-name"
                placeholder="e.g., John Doe or user@example.com"
                value={approverName}
                onChange={(e) => setApproverName(e.target.value)}
                className="bg-brain-bg border-white/10"
              />
            </div>
            <Badge variant="outline" className="border-brain-gold/50 text-brain-gold">
              Required for all approvals
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="queue" className="space-y-4">
        <TabsList className="bg-brain-panel border border-white/5">
          <TabsTrigger value="queue" className="data-[state=active]:bg-brain-accent">
            <Clock className="w-4 h-4 mr-2" />
            Pending Queue ({queue.data?.total ?? 0})
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-brain-accent">
            <FileText className="w-4 h-4 mr-2" />
            History
          </TabsTrigger>
        </TabsList>

        {/* Pending Queue Tab */}
        <TabsContent value="queue" className="space-y-4">
          {queue.isLoading && (
            <Card className="brain-card">
              <CardContent className="pt-6">
                <p className="text-center text-muted-foreground">Loading pending approvals...</p>
              </CardContent>
            </Card>
          )}

          {queue.data?.total === 0 && (
            <Card className="brain-card border-green-500/20">
              <CardContent className="pt-6">
                <div className="text-center">
                  <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
                  <p className="font-semibold">No pending approvals</p>
                  <p className="text-sm text-muted-foreground">All HIGH/CRITICAL risk actions have been reviewed</p>
                </div>
              </CardContent>
            </Card>
          )}

          {queue.data?.pending.map((approval) => (
            <Card key={approval.token} className="brain-card border-yellow-500/30">
              <CardHeader className="brain-card-header">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="brain-card-title flex items-center gap-2">
                      <ShieldAlert className="w-5 h-5 text-yellow-500" />
                      {approval.action}
                      <Badge
                        variant="outline"
                        className={
                          approval.risk_level === "critical"
                            ? "border-red-500/50 text-red-500"
                            : "border-yellow-500/50 text-yellow-500"
                        }
                      >
                        {approval.risk_level.toUpperCase()}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Requested by <strong>{approval.requesting_agent}</strong> • Token: <code className="text-xs">{approval.token}</code>
                    </CardDescription>
                  </div>
                  <div className="text-right">
                    {approval.time_remaining && approval.time_remaining > 0 ? (
                      <div className="flex items-center gap-1 text-sm text-yellow-500">
                        <Clock className="w-4 h-4" />
                        {Math.floor(approval.time_remaining / 60)}m {approval.time_remaining % 60}s
                      </div>
                    ) : (
                      <Badge variant="outline" className="border-red-500/50 text-red-500">
                        Expired
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Context */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Context:</h4>
                    <pre className="bg-brain-bg p-3 rounded text-xs overflow-x-auto border border-white/5">
                      {JSON.stringify(approval.context, null, 2)}
                    </pre>
                  </div>

                  {/* Metadata */}
                  <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
                    <div>
                      <strong>Created:</strong> {new Date(approval.created_at).toLocaleString()}
                    </div>
                    <div>
                      <strong>Audit ID:</strong> {approval.audit_id}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-2">
                    <Button
                      onClick={() => setSelectedApproval(approval)}
                      disabled={!approverName.trim() || approval.is_expired}
                      className="flex-1"
                    >
                      Review & Decide
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {queue.data && queue.data.expired > 0 && (
            <Card className="brain-card border-red-500/20">
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 text-sm text-red-500">
                  <AlertCircle className="w-4 h-4" />
                  {queue.data.expired} request(s) have expired and were automatically denied
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4">
          {/* Filter */}
          <Card className="brain-card">
            <CardContent className="pt-6">
              <div className="flex gap-2">
                <Button
                  variant={historyStatus === undefined ? "default" : "outline"}
                  size="sm"
                  onClick={() => setHistoryStatus(undefined)}
                >
                  All
                </Button>
                <Button
                  variant={historyStatus === "approved" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setHistoryStatus("approved")}
                >
                  Approved
                </Button>
                <Button
                  variant={historyStatus === "denied" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setHistoryStatus("denied")}
                >
                  Denied
                </Button>
                <Button
                  variant={historyStatus === "expired" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setHistoryStatus("expired")}
                >
                  Expired
                </Button>
              </div>
            </CardContent>
          </Card>

          {history.isLoading && (
            <Card className="brain-card">
              <CardContent className="pt-6">
                <p className="text-center text-muted-foreground">Loading history...</p>
              </CardContent>
            </Card>
          )}

          {history.data?.approvals.map((approval) => (
            <Card key={approval.token} className="brain-card">
              <CardHeader className="brain-card-header">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="brain-card-title flex items-center gap-2">
                      {approval.status === "approved" ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      ) : approval.status === "denied" ? (
                        <XCircle className="w-5 h-5 text-red-500" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-gray-500" />
                      )}
                      {approval.action}
                      <Badge
                        variant="outline"
                        className={
                          approval.status === "approved"
                            ? "border-green-500/50 text-green-500"
                            : approval.status === "denied"
                            ? "border-red-500/50 text-red-500"
                            : "border-gray-500/50 text-gray-500"
                        }
                      >
                        {approval.status.toUpperCase()}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {approval.requesting_agent} • {approval.risk_level.toUpperCase()} risk
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {approval.approved_by && (
                    <div>
                      <strong>Approved by:</strong> {approval.approved_by}
                    </div>
                  )}
                  {approval.approval_timestamp && (
                    <div>
                      <strong>Decision time:</strong> {new Date(approval.approval_timestamp).toLocaleString()}
                    </div>
                  )}
                  {approval.approval_reason && (
                    <div>
                      <strong>Reason:</strong> {approval.approval_reason}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>

      {/* Approval Dialog */}
      <Dialog open={!!selectedApproval} onOpenChange={(open) => !open && setSelectedApproval(null)}>
        <DialogContent className="bg-brain-panel border border-white/10 max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-yellow-500" />
              Review Approval Request
            </DialogTitle>
            <DialogDescription>
              Carefully review the details below before making a decision
            </DialogDescription>
          </DialogHeader>

          {selectedApproval && (
            <div className="space-y-4">
              {/* Summary */}
              <Card className="brain-card border-yellow-500/30">
                <CardContent className="pt-6 space-y-2 text-sm">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <strong>Action:</strong> {selectedApproval.action}
                    </div>
                    <div>
                      <strong>Risk Level:</strong>{" "}
                      <Badge
                        variant="outline"
                        className={
                          selectedApproval.risk_level === "critical"
                            ? "border-red-500/50 text-red-500"
                            : "border-yellow-500/50 text-yellow-500"
                        }
                      >
                        {selectedApproval.risk_level.toUpperCase()}
                      </Badge>
                    </div>
                    <div>
                      <strong>Agent:</strong> {selectedApproval.requesting_agent}
                    </div>
                    <div>
                      <strong>Token:</strong> <code className="text-xs">{selectedApproval.token}</code>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Context */}
              <div>
                <Label>Context:</Label>
                <pre className="bg-brain-bg p-3 rounded text-xs overflow-x-auto border border-white/5 mt-2">
                  {JSON.stringify(selectedApproval.context, null, 2)}
                </pre>
              </div>

              {/* Reason */}
              <div>
                <Label htmlFor="approval-reason">Decision Reason (Optional)</Label>
                <Textarea
                  id="approval-reason"
                  placeholder="Explain your decision..."
                  value={approvalReason}
                  onChange={(e) => setApprovalReason(e.target.value)}
                  className="bg-brain-bg border-white/10 mt-2"
                  rows={3}
                />
              </div>

              {/* Approver */}
              <div className="bg-brain-accent/20 p-3 rounded border border-brain-gold/20">
                <p className="text-sm">
                  <strong>Approver:</strong> {approverName}
                </p>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setSelectedApproval(null)}
              disabled={approveMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="outline"
              className="border-red-500/50 text-red-500 hover:bg-red-500/10"
              onClick={() => selectedApproval && handleApprove(selectedApproval, false)}
              disabled={approveMutation.isPending}
            >
              <XCircle className="w-4 h-4 mr-2" />
              Deny
            </Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={() => selectedApproval && handleApprove(selectedApproval, true)}
              disabled={approveMutation.isPending}
            >
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

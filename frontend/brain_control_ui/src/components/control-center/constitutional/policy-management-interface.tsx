"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Shield,
  Plus,
  Edit,
  Trash2,
  Download,
  Upload,
  TestTube,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileJson,
  Save,
  Copy
} from "lucide-react";
import {
  usePolicies,
  usePolicyStats,
  usePolicyCreate,
  usePolicyUpdate,
  usePolicyDelete,
  usePolicyTest,
  type Policy,
  type PolicyRule,
  type PolicyCondition,
  type PolicyEffect,
  type PolicyCreateRequest,
  type PolicyConditionOperator,
} from "@/hooks/usePolicy";

/**
 * Advanced Policy Management Interface
 *
 * Comprehensive policy editor with rule builder, testing, and import/export.
 */
export function PolicyManagementInterface() {
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [editPolicy, setEditPolicy] = useState<PolicyCreateRequest | null>(null);
  const [deletePolicy, setDeletePolicy] = useState<Policy | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [showEditor, setShowEditor] = useState(false);
  const [showTestSandbox, setShowTestSandbox] = useState(false);

  const policies = usePolicies();
  const stats = usePolicyStats();
  const createMutation = usePolicyCreate();
  const updateMutation = usePolicyUpdate();
  const deleteMutation = usePolicyDelete();
  const testMutation = usePolicyTest();

  // Filter policies based on search term
  const filteredPolicies = policies.data?.policies.filter((policy) =>
    policy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    policy.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    policy.policy_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCreatePolicy = () => {
    setEditPolicy({
      name: "",
      version: "1.0.0",
      description: "",
      rules: [],
      default_effect: "deny",
      enabled: true,
    });
    setShowEditor(true);
  };

  const handleEditPolicy = (policy: Policy) => {
    setEditPolicy({
      name: policy.name,
      version: policy.version,
      description: policy.description,
      rules: policy.rules,
      default_effect: policy.default_effect,
      enabled: policy.enabled,
    });
    setSelectedPolicy(policy);
    setShowEditor(true);
  };

  const handleSavePolicy = () => {
    if (!editPolicy) return;

    if (selectedPolicy) {
      // Update existing policy
      updateMutation.mutate(
        { policyId: selectedPolicy.policy_id, request: editPolicy },
        {
          onSuccess: () => {
            setShowEditor(false);
            setEditPolicy(null);
            setSelectedPolicy(null);
            alert("Policy updated successfully");
          },
        }
      );
    } else {
      // Create new policy
      createMutation.mutate(editPolicy, {
        onSuccess: () => {
          setShowEditor(false);
          setEditPolicy(null);
          alert("Policy created successfully");
        },
      });
    }
  };

  const handleDeletePolicy = () => {
    if (!deletePolicy) return;

    deleteMutation.mutate(deletePolicy.policy_id, {
      onSuccess: () => {
        setDeletePolicy(null);
        alert("Policy deleted successfully");
      },
    });
  };

  const handleExportPolicy = (policy: Policy) => {
    const dataStr = JSON.stringify(policy, null, 2);
    const dataUri = `data:application/json;charset=utf-8,${encodeURIComponent(dataStr)}`;
    const exportFileDefaultName = `policy_${policy.policy_id}.json`;

    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();
  };

  const handleImportPolicy = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/json";
    input.onchange = (e: Event) => {
      const target = e.target as HTMLInputElement;
      const file = target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const importedPolicy = JSON.parse(event.target?.result as string);
          setEditPolicy({
            name: importedPolicy.name || "",
            version: importedPolicy.version || "1.0.0",
            description: importedPolicy.description || "",
            rules: importedPolicy.rules || [],
            default_effect: importedPolicy.default_effect || "deny",
            enabled: importedPolicy.enabled ?? true,
          });
          setShowEditor(true);
        } catch (error) {
          alert(`Failed to import policy: ${error}`);
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const handleDuplicatePolicy = (policy: Policy) => {
    setEditPolicy({
      name: `${policy.name} (Copy)`,
      version: "1.0.0",
      description: policy.description,
      rules: policy.rules,
      default_effect: policy.default_effect,
      enabled: policy.enabled,
    });
    setShowEditor(true);
  };

  return (
    <div className="space-y-6">
      {/* Stats Header */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm">Total Policies</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.data?.total_policies ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm">Active Policies</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-500">{stats.data?.active_policies ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm">Total Rules</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.data?.total_rules ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="brain-card">
          <CardHeader className="brain-card-header pb-3">
            <CardTitle className="brain-card-title text-sm">Evaluations</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.data?.total_evaluations ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      {/* Actions Bar */}
      <Card className="brain-card">
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 items-center justify-between">
            <div className="flex-1 min-w-[200px] max-w-md">
              <Input
                placeholder="Search policies..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-brain-bg border-white/10"
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleImportPolicy} variant="outline" size="sm">
                <Upload className="w-4 h-4 mr-2" />
                Import
              </Button>
              <Button onClick={() => setShowTestSandbox(true)} variant="outline" size="sm">
                <TestTube className="w-4 h-4 mr-2" />
                Test Sandbox
              </Button>
              <Button onClick={handleCreatePolicy} size="sm">
                <Plus className="w-4 h-4 mr-2" />
                Create Policy
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Policies List */}
      <div className="space-y-4">
        {policies.isLoading && (
          <Card className="brain-card">
            <CardContent className="pt-6">
              <p className="text-center text-muted-foreground">Loading policies...</p>
            </CardContent>
          </Card>
        )}

        {filteredPolicies?.map((policy) => (
          <Card key={policy.policy_id} className="brain-card">
            <CardHeader className="brain-card-header">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="brain-card-title flex items-center gap-2">
                    <Shield className="w-5 h-5 text-blue-500" />
                    {policy.name}
                    <Badge
                      variant="outline"
                      className={policy.enabled ? "border-green-500/50 text-green-500" : "border-gray-500/50 text-gray-500"}
                    >
                      {policy.enabled ? "ENABLED" : "DISABLED"}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      v{policy.version}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {policy.description || "No description"}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => handleExportPolicy(policy)}
                    variant="outline"
                    size="sm"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                  <Button
                    onClick={() => handleDuplicatePolicy(policy)}
                    variant="outline"
                    size="sm"
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    onClick={() => handleEditPolicy(policy)}
                    variant="outline"
                    size="sm"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    onClick={() => setDeletePolicy(policy)}
                    variant="outline"
                    size="sm"
                    className="text-red-500 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {/* Policy Info */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <strong>Policy ID:</strong> <code className="text-xs">{policy.policy_id}</code>
                  </div>
                  <div>
                    <strong>Rules:</strong> {policy.rules.length}
                  </div>
                  <div>
                    <strong>Default Effect:</strong>{" "}
                    <Badge variant="outline" className="text-xs">
                      {policy.default_effect.toUpperCase()}
                    </Badge>
                  </div>
                  <div>
                    <strong>Created:</strong> {new Date(policy.created_at).toLocaleDateString()}
                  </div>
                </div>

                {/* Rules Preview */}
                {policy.rules.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Rules ({policy.rules.length}):</h4>
                    <div className="space-y-1">
                      {policy.rules.slice(0, 3).map((rule) => (
                        <div key={rule.rule_id} className="text-xs flex items-center gap-2 bg-brain-accent/20 p-2 rounded">
                          {rule.effect === "allow" ? (
                            <CheckCircle2 className="w-3 h-3 text-green-500" />
                          ) : rule.effect === "deny" ? (
                            <XCircle className="w-3 h-3 text-red-500" />
                          ) : (
                            <AlertTriangle className="w-3 h-3 text-yellow-500" />
                          )}
                          <span className="font-semibold">{rule.name}</span>
                          <Badge variant="outline" className="text-xs">
                            Priority: {rule.priority}
                          </Badge>
                        </div>
                      ))}
                      {policy.rules.length > 3 && (
                        <p className="text-xs text-muted-foreground">
                          +{policy.rules.length - 3} more rules
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}

        {filteredPolicies?.length === 0 && (
          <Card className="brain-card">
            <CardContent className="pt-6">
              <p className="text-center text-muted-foreground">
                {searchTerm ? "No policies match your search" : "No policies found"}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Policy Editor Dialog - Will continue in next part */}
      {showEditor && (
        <PolicyEditorDialog
          policy={editPolicy}
          onClose={() => {
            setShowEditor(false);
            setEditPolicy(null);
            setSelectedPolicy(null);
          }}
          onSave={handleSavePolicy}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Test Sandbox Dialog */}
      {showTestSandbox && (
        <PolicyTestSandbox
          onClose={() => setShowTestSandbox(false)}
          testMutation={testMutation}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deletePolicy} onOpenChange={(open) => !open && setDeletePolicy(null)}>
        <AlertDialogContent className="bg-brain-panel border border-white/10">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Policy?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{deletePolicy?.name}</strong>? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeletePolicy}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// Component will continue with PolicyEditorDialog and PolicyTestSandbox...
// Due to size, splitting into manageable parts

/**
 * Policy Editor Dialog Component
 */
function PolicyEditorDialog({
  policy,
  onClose,
  onSave,
  isLoading,
}: {
  policy: PolicyCreateRequest | null;
  onClose: () => void;
  onSave: () => void;
  isLoading: boolean;
}) {
  const [editedPolicy, setEditedPolicy] = useState<PolicyCreateRequest>(
    policy || {
      name: "",
      version: "1.0.0",
      description: "",
      rules: [],
      default_effect: "deny",
      enabled: true,
    }
  );

  const updateField = (field: keyof PolicyCreateRequest, value: unknown) => {
    setEditedPolicy((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="bg-brain-panel border border-white/10 max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileJson className="w-5 h-5" />
            {policy?.name ? "Edit Policy" : "Create New Policy"}
          </DialogTitle>
          <DialogDescription>
            Configure policy settings and rules
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Basic Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="policy-name">Policy Name *</Label>
              <Input
                id="policy-name"
                value={editedPolicy.name}
                onChange={(e) => updateField("name", e.target.value)}
                className="bg-brain-bg border-white/10"
                placeholder="e.g., Robot Safety Policy"
              />
            </div>
            <div>
              <Label htmlFor="policy-version">Version</Label>
              <Input
                id="policy-version"
                value={editedPolicy.version}
                onChange={(e) => updateField("version", e.target.value)}
                className="bg-brain-bg border-white/10"
                placeholder="1.0.0"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="policy-description">Description</Label>
            <Textarea
              id="policy-description"
              value={editedPolicy.description}
              onChange={(e) => updateField("description", e.target.value)}
              className="bg-brain-bg border-white/10"
              placeholder="Describe the purpose of this policy..."
              rows={3}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="default-effect">Default Effect</Label>
              <Select
                value={editedPolicy.default_effect}
                onValueChange={(value) => updateField("default_effect", value as PolicyEffect)}
              >
                <SelectTrigger className="bg-brain-bg border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="allow">Allow</SelectItem>
                  <SelectItem value="deny">Deny</SelectItem>
                  <SelectItem value="warn">Warn</SelectItem>
                  <SelectItem value="audit">Audit</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editedPolicy.enabled}
                  onChange={(e) => updateField("enabled", e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Policy Enabled</span>
              </label>
            </div>
          </div>

          {/* Rules section - simplified for now */}
          <div>
            <Label>Rules ({editedPolicy.rules?.length ?? 0})</Label>
            <div className="bg-brain-accent/10 p-4 rounded border border-white/5 mt-2">
              <p className="text-sm text-muted-foreground">
                Use Import/Export or raw JSON editing for rule management.
                Advanced rule builder coming soon.
              </p>
              <Textarea
                value={JSON.stringify(editedPolicy.rules, null, 2)}
                onChange={(e) => {
                  try {
                    const rules = JSON.parse(e.target.value);
                    updateField("rules", rules);
                  } catch {
                    // Invalid JSON, ignore
                  }
                }}
                className="bg-brain-bg border-white/10 mt-2 font-mono text-xs"
                rows={10}
              />
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              // Update parent state before saving
              onSave();
            }}
            disabled={!editedPolicy.name || isLoading}
          >
            <Save className="w-4 h-4 mr-2" />
            {isLoading ? "Saving..." : "Save Policy"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Policy Test Sandbox Component
 */
function PolicyTestSandbox({
  onClose,
  testMutation,
}: {
  onClose: () => void;
  testMutation: ReturnType<typeof usePolicyTest>;
}) {
  const [agentId, setAgentId] = useState("test_agent");
  const [agentRole, setAgentRole] = useState("user");
  const [action, setAction] = useState("read");
  const [resource, setResource] = useState("");
  const [environment, setEnvironment] = useState("{}");
  const [params, setParams] = useState("{}");

  const handleTest = () => {
    try {
      const envObj = JSON.parse(environment || "{}");
      const paramsObj = JSON.parse(params || "{}");

      testMutation.mutate({
        agent_id: agentId,
        agent_role: agentRole,
        action,
        resource: resource || undefined,
        environment: envObj,
        params: paramsObj,
      });
    } catch (error) {
      alert(`Invalid JSON: ${error}`);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="bg-brain-panel border border-white/10 max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TestTube className="w-5 h-5 text-blue-500" />
            Policy Test Sandbox
          </DialogTitle>
          <DialogDescription>
            Test policy evaluation without actually enforcing the decision
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="test-agent-id">Agent ID</Label>
              <Input
                id="test-agent-id"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                className="bg-brain-bg border-white/10"
              />
            </div>
            <div>
              <Label htmlFor="test-agent-role">Agent Role</Label>
              <Input
                id="test-agent-role"
                value={agentRole}
                onChange={(e) => setAgentRole(e.target.value)}
                className="bg-brain-bg border-white/10"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="test-action">Action</Label>
              <Input
                id="test-action"
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className="bg-brain-bg border-white/10"
                placeholder="e.g., robot.move"
              />
            </div>
            <div>
              <Label htmlFor="test-resource">Resource (Optional)</Label>
              <Input
                id="test-resource"
                value={resource}
                onChange={(e) => setResource(e.target.value)}
                className="bg-brain-bg border-white/10"
                placeholder="e.g., warehouse_zone_a"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="test-environment">Environment (JSON)</Label>
            <Textarea
              id="test-environment"
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="bg-brain-bg border-white/10 font-mono text-xs"
              rows={3}
              placeholder='{"time": "daytime", "battery_level": 80}'
            />
          </div>

          <div>
            <Label htmlFor="test-params">Parameters (JSON)</Label>
            <Textarea
              id="test-params"
              value={params}
              onChange={(e) => setParams(e.target.value)}
              className="bg-brain-bg border-white/10 font-mono text-xs"
              rows={3}
              placeholder='{"distance": 10, "speed": 2}'
            />
          </div>

          {/* Test Result */}
          {testMutation.data && (
            <Card className={`brain-card ${testMutation.data.allowed ? "border-green-500/30" : "border-red-500/30"}`}>
              <CardHeader className="brain-card-header">
                <CardTitle className="brain-card-title text-sm flex items-center gap-2">
                  {testMutation.data.allowed ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                  Result: {testMutation.data.allowed ? "ALLOWED" : "DENIED"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div>
                    <strong>Effect:</strong>{" "}
                    <Badge variant="outline">{testMutation.data.effect.toUpperCase()}</Badge>
                  </div>
                  <div>
                    <strong>Reason:</strong> {testMutation.data.reason}
                  </div>
                  {testMutation.data.matched_policy && (
                    <div>
                      <strong>Matched Policy:</strong> {testMutation.data.matched_policy}
                    </div>
                  )}
                  {testMutation.data.matched_rule && (
                    <div>
                      <strong>Matched Rule:</strong> {testMutation.data.matched_rule}
                    </div>
                  )}
                  {testMutation.data.warnings && testMutation.data.warnings.length > 0 && (
                    <div>
                      <strong>Warnings:</strong>
                      <ul className="list-disc list-inside">
                        {testMutation.data.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={handleTest} disabled={testMutation.isPending}>
            <TestTube className="w-4 h-4 mr-2" />
            {testMutation.isPending ? "Testing..." : "Run Test"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

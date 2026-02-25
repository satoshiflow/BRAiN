"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from "@ui-core/components";
import { useWorkspaces, useWorkspaceStats, useCreateWorkspace } from "@/hooks/use-api";
import { Plus, Zap, Package, HardDrive, AlertCircle } from "lucide-react";
import { useState } from "react";
import Link from "next/link";

export default function AutonomousPipelinePage() {
  const { data: workspaces = [], isLoading: workspacesLoading } = useWorkspaces();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const { data: stats } = useWorkspaceStats(selectedWorkspaceId || "");
  const createWorkspaceMutation = useCreateWorkspace();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newWorkspaceData, setNewWorkspaceData] = useState({
    name: "",
    slug: "",
    description: "",
    max_projects: 100,
    max_runs_per_day: 1000,
    max_storage_gb: 100.0,
  });

  const handleCreateWorkspace = async () => {
    try {
      await createWorkspaceMutation.mutateAsync(newWorkspaceData);
      setShowCreateForm(false);
      setNewWorkspaceData({
        name: "",
        slug: "",
        description: "",
        max_projects: 100,
        max_runs_per_day: 1000,
        max_storage_gb: 100.0,
      });
    } catch (error) {
      console.error("Failed to create workspace:", error);
    }
  };

  if (workspacesLoading) {
    return <div className="p-8">Loading workspaces...</div>;
  }

  const activeWorkspace = workspaces.find((w) => w.workspace_id === selectedWorkspaceId);

  return (
    <DashboardLayout
      title="Autonomous Pipeline"
      subtitle="Multi-tenant workspace management and pipeline execution"
    >
      <PageContainer>
        <PageHeader
          title="Workspace Management"
          description="Create and manage isolated execution workspaces with quota enforcement"
        />

        {/* Quick Actions */}
        <div className="flex gap-3 mb-6">
          <Button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="flex items-center gap-2"
          >
            <Plus size={18} />
            New Workspace
          </Button>
        </div>

        {/* Create Workspace Form */}
        {showCreateForm && (
          <Card className="mb-6 bg-blue-50">
            <CardHeader>
              <CardTitle className="text-lg">Create New Workspace</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Workspace Name</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newWorkspaceData.name}
                    onChange={(e) =>
                      setNewWorkspaceData({ ...newWorkspaceData, name: e.target.value })
                    }
                    placeholder="e.g., Production Workspace"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Slug</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newWorkspaceData.slug}
                    onChange={(e) =>
                      setNewWorkspaceData({ ...newWorkspaceData, slug: e.target.value })
                    }
                    placeholder="e.g., prod-ws"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-2">Description</label>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newWorkspaceData.description}
                    onChange={(e) =>
                      setNewWorkspaceData({ ...newWorkspaceData, description: e.target.value })
                    }
                    placeholder="Workspace description"
                    rows={2}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Projects</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newWorkspaceData.max_projects}
                    onChange={(e) =>
                      setNewWorkspaceData({
                        ...newWorkspaceData,
                        max_projects: parseInt(e.target.value) || 100,
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Runs/Day</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newWorkspaceData.max_runs_per_day}
                    onChange={(e) =>
                      setNewWorkspaceData({
                        ...newWorkspaceData,
                        max_runs_per_day: parseInt(e.target.value) || 1000,
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Storage (GB)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newWorkspaceData.max_storage_gb}
                    onChange={(e) =>
                      setNewWorkspaceData({
                        ...newWorkspaceData,
                        max_storage_gb: parseFloat(e.target.value) || 100.0,
                      })
                    }
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-4">
                <Button
                  onClick={handleCreateWorkspace}
                  className="bg-blue-600 text-white"
                  disabled={createWorkspaceMutation.isPending || !newWorkspaceData.name}
                >
                  Create Workspace
                </Button>
                <Button
                  onClick={() => setShowCreateForm(false)}
                  className="bg-gray-200"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Workspaces Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {workspaces.map((workspace) => (
            <Card
              key={workspace.workspace_id}
              className={`cursor-pointer hover:shadow-lg transition-shadow ${
                selectedWorkspaceId === workspace.workspace_id
                  ? "ring-2 ring-blue-500"
                  : ""
              }`}
              onClick={() => setSelectedWorkspaceId(workspace.workspace_id)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base">{workspace.name}</CardTitle>
                    <p className="text-xs text-gray-500 mt-1">{workspace.slug}</p>
                  </div>
                  <Badge
                    variant={workspace.status === "active" ? "success" : "warning"}
                  >
                    {workspace.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 mb-3">{workspace.description}</p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Projects:</span>
                    <span className="font-medium">
                      0/{workspace.max_projects}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Daily Runs:</span>
                    <span className="font-medium">
                      0/{workspace.max_runs_per_day}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Storage:</span>
                    <span className="font-medium">
                      0/{workspace.max_storage_gb}GB
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Selected Workspace Details */}
        {activeWorkspace && (
          <>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">{activeWorkspace.name} - Details</h2>
              <Link
                href={`/modules/autonomous-pipeline/${activeWorkspace.workspace_id}`}
              >
                <Button className="flex items-center gap-2">
                  <Zap size={18} />
                  Manage Workspace
                </Button>
              </Link>
            </div>

            {/* Workspace Stats */}
            {stats && (
              <Grid cols={4} gap="md">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Package size={16} />
                      Projects
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {stats.total_projects}
                    </div>
                    <p className="text-xs text-gray-500">
                      {stats.active_projects} active
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Zap size={16} />
                      Daily Runs
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {stats.runs_today}
                    </div>
                    <p className="text-xs text-gray-500">
                      {stats.total_runs} total
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <HardDrive size={16} />
                      Storage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {stats.storage_used_gb.toFixed(2)}GB
                    </div>
                    <p className="text-xs text-gray-500">
                      of {stats.storage_limit_gb}GB
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <AlertCircle size={16} />
                      Quota Usage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {stats.quota_usage_percent.toFixed(1)}%
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min(stats.quota_usage_percent, 100)}%`,
                        }}
                      />
                    </div>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </>
        )}
      </PageContainer>
    </DashboardLayout>
  );
}

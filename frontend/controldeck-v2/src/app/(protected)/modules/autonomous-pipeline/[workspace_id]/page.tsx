"use client";

import { useParams } from "next/navigation";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from "@ui-core/components";
import {
  useWorkspace,
  useWorkspaceStats,
  useProjects,
  useCreateProject,
  useDeleteProject,
  useUpdateWorkspace,
} from "@/hooks/use-api";
import { Plus, Trash2, Edit2, ArrowLeft, HardDrive, Zap, CheckCircle, AlertCircle } from "lucide-react";
import { useState } from "react";
import Link from "next/link";

export default function WorkspaceDetailPage() {
  const params = useParams();
  const workspaceId = params.workspace_id as string;

  const { data: workspace, isLoading: workspaceLoading } = useWorkspace(workspaceId);
  const { data: stats, isLoading: statsLoading } = useWorkspaceStats(workspaceId);
  const { data: projects = [], isLoading: projectsLoading } = useProjects(workspaceId);
  const createProjectMutation = useCreateProject(workspaceId);
  const deleteProjectMutation = useDeleteProject(workspaceId);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProjectData, setNewProjectData] = useState({
    name: "",
    slug: "",
    description: "",
  });

  const handleCreateProject = async () => {
    try {
      await createProjectMutation.mutateAsync(newProjectData);
      setShowCreateForm(false);
      setNewProjectData({
        name: "",
        slug: "",
        description: "",
      });
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (confirm("Are you sure you want to delete this project?")) {
      try {
        await deleteProjectMutation.mutateAsync(projectId);
      } catch (error) {
        console.error("Failed to delete project:", error);
      }
    }
  };

  if (workspaceLoading || statsLoading) {
    return <div className="p-8">Loading workspace details...</div>;
  }

  if (!workspace) {
    return <div className="p-8">Workspace not found</div>;
  }

  return (
    <DashboardLayout
      title={workspace.name}
      subtitle="Workspace projects and execution history"
    >
      <PageContainer>
        {/* Header with Back Button */}
        <div className="flex items-center gap-4 mb-6">
          <Link href="/modules/autonomous-pipeline">
            <Button className="flex items-center gap-2 bg-gray-200">
              <ArrowLeft size={18} />
              Back
            </Button>
          </Link>
          <div className="flex-1">
            <PageHeader
              title={workspace.name}
              description={workspace.description || "No description"}
            />
          </div>
          <Badge variant={workspace.status === "active" ? "success" : "warning"}>
            {workspace.status}
          </Badge>
        </div>

        {/* Workspace Stats */}
        {stats && (
          <Grid cols={4} gap="md" className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Active Projects</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.active_projects}</div>
                <p className="text-xs text-gray-500 mt-1">
                  of {stats.total_projects} total
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Today&apos;s Runs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.runs_today}</div>
                <p className="text-xs text-gray-500 mt-1">
                  {stats.total_runs} total runs
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Storage Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {stats.storage_used_gb.toFixed(2)}GB
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  of {stats.storage_limit_gb}GB
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Quota Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {stats.quota_usage_percent.toFixed(0)}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      stats.quota_usage_percent > 80
                        ? "bg-red-600"
                        : stats.quota_usage_percent > 60
                        ? "bg-yellow-600"
                        : "bg-green-600"
                    }`}
                    style={{
                      width: `${Math.min(stats.quota_usage_percent, 100)}%`,
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Projects Section */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold">Projects</h2>
            <Button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="flex items-center gap-2"
            >
              <Plus size={18} />
              New Project
            </Button>
          </div>

          {/* Create Project Form */}
          {showCreateForm && (
            <Card className="mb-6 bg-blue-50">
              <CardHeader>
                <CardTitle className="text-lg">Create New Project</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Project Name</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      value={newProjectData.name}
                      onChange={(e) =>
                        setNewProjectData({ ...newProjectData, name: e.target.value })
                      }
                      placeholder="e.g., E-Commerce Platform"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Slug</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      value={newProjectData.slug}
                      onChange={(e) =>
                        setNewProjectData({ ...newProjectData, slug: e.target.value })
                      }
                      placeholder="e.g., ecommerce"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium mb-2">Description</label>
                    <textarea
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      value={newProjectData.description}
                      onChange={(e) =>
                        setNewProjectData({ ...newProjectData, description: e.target.value })
                      }
                      placeholder="Project description"
                      rows={2}
                    />
                  </div>
                </div>
                <div className="flex gap-3 mt-4">
                  <Button
                    onClick={handleCreateProject}
                    className="bg-blue-600 text-white"
                    disabled={createProjectMutation.isPending || !newProjectData.name}
                  >
                    Create Project
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

          {/* Projects List */}
          {projectsLoading ? (
            <div className="text-center text-gray-500 py-8">Loading projects...</div>
          ) : projects.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8 text-gray-500">
                No projects yet. Create one to get started!
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {projects.map((project) => (
                <Card key={project.project_id}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-base">{project.name}</CardTitle>
                        <p className="text-xs text-gray-500 mt-1">{project.slug}</p>
                      </div>
                      <Badge
                        variant={
                          project.status === "active"
                            ? "success"
                            : project.status === "paused"
                            ? "warning"
                            : "secondary"
                        }
                      >
                        {project.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 mb-4">{project.description}</p>

                    <div className="space-y-2 mb-4 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 flex items-center gap-2">
                          <Zap size={14} />
                          Total Runs
                        </span>
                        <span className="font-medium">{project.total_runs}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 flex items-center gap-2">
                          <CheckCircle size={14} />
                          Successful
                        </span>
                        <span className="font-medium text-green-600">
                          {project.successful_runs}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 flex items-center gap-2">
                          <AlertCircle size={14} />
                          Failed
                        </span>
                        <span className="font-medium text-red-600">
                          {project.failed_runs}
                        </span>
                      </div>
                      {project.total_runs > 0 && (
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">Success Rate</span>
                          <span className="font-medium">
                            {(
                              (project.successful_runs / project.total_runs) *
                              100
                            ).toFixed(1)}
                            %
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex gap-2 pt-4 border-t">
                      <Link
                        href={`/modules/autonomous-pipeline/${workspaceId}/${project.project_id}`}
                        className="flex-1"
                      >
                        <Button className="w-full bg-blue-600 text-white text-sm">
                          View Details
                        </Button>
                      </Link>
                      <Button
                        onClick={() => handleDeleteProject(project.project_id)}
                        className="bg-red-600 text-white px-3"
                        disabled={deleteProjectMutation.isPending}
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </PageContainer>
    </DashboardLayout>
  );
}

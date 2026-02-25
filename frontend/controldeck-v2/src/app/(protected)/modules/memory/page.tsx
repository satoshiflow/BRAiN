"use client";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@ui-core/components";
import { useMemory } from "@/hooks/use-api";
import { RefreshCw } from "lucide-react";

export default function MemoryPage() {
  const { data: memoryInfo, isLoading } = useMemory();

  if (isLoading) return <div>Loading...</div>;

  return (
    <DashboardLayout
      title="Memory"
      subtitle="Agent memory management and context tracking"
    >
      <PageContainer>
        <PageHeader
          title="Memory Management"
          description="Track agent memory, sessions, and context windows"
        />

        {/* Stats Cards */}
        <Grid cols={3} gap="md">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Total Entries</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {memoryInfo?.total_entries || 0}
              </div>
              <p className="text-xs text-gray-500">Episodic + Semantic</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Active Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {memoryInfo?.active_sessions || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Avg Session Tokens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {memoryInfo?.avg_tokens || 0}
              </div>
            </CardContent>
          </Card>
        </Grid>

        {/* Memory Breakdown */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Memory Layers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span>Episodic Memories</span>
                <Badge>{memoryInfo?.episodic_count || 0}</Badge>
              </div>
              <div className="flex justify-between">
                <span>Semantic Memories</span>
                <Badge>{memoryInfo?.semantic_count || 0}</Badge>
              </div>
              <div className="flex justify-between">
                <span>Working Memory Sessions</span>
                <Badge>{memoryInfo?.working_count || 0}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}

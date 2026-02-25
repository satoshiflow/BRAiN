"use client";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader, Grid } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@ui-core/components";
import { useLearning } from "@/hooks/use-api";
import { Plus } from "lucide-react";

export default function LearningPage() {
  const { data: stats, isLoading } = useLearning();

  if (isLoading) return <div>Loading...</div>;

  return (
    <DashboardLayout
      title="Learning"
      subtitle="A/B testing, strategy selection, and performance metrics"
    >
      <PageContainer>
        <PageHeader
          title="Learning Management"
          description="Agent learning strategies, experiments, and metrics"
        />

        {/* Stats Grid */}
        <Grid cols={4} gap="md">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Active Strategies</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.active_strategies || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Total Strategies</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.total_strategies || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Metrics Recorded</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.total_metrics_recorded || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Running Experiments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.running_experiments || 0}
              </div>
              <p className="text-xs text-gray-500">Active</p>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Experiments Card */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Active A/B Experiments</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-gray-500 text-sm">
              {stats?.running_experiments || 0} experiments running
            </div>
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}

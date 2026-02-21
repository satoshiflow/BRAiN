"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, Badge, Button, Skeleton } from "@ui-core/components";
import { useEvents, useEventStats } from "@/hooks/use-api";
import { formatRelativeTime } from "@ui-core/utils";
import { 
  Filter, 
  Search,
  AlertCircle,
  CheckCircle,
  Info,
  XCircle,
  Clock,
  RefreshCw
} from "lucide-react";
import { useState } from "react";

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case "error":
    case "critical":
      return <XCircle className="h-5 w-5 text-danger" />;
    case "warning":
      return <AlertCircle className="h-5 w-5 text-warning" />;
    case "success":
      return <CheckCircle className="h-5 w-5 text-success" />;
    default:
      return <Info className="h-5 w-5 text-info" />;
  }
};

const getSeverityBadge = (severity: string) => {
  switch (severity) {
    case "error":
    case "critical":
      return <Badge variant="danger">Error</Badge>;
    case "warning":
      return <Badge variant="warning">Warning</Badge>;
    case "success":
      return <Badge variant="success">Success</Badge>;
    default:
      return <Badge variant="info">Info</Badge>;
  }
};

export default function EventsPage() {
  const [filter, setFilter] = useState<string>('all');
  const { data: eventsData, isLoading, isError, refetch } = useEvents({ limit: 100 });
  const { data: statsData } = useEventStats();

  const events = eventsData ?? [];
  const filteredEvents = filter === 'all' 
    ? events 
    : events.filter(e => e.severity === filter);

  if (isError) {
    return (
      <DashboardLayout title="Events" subtitle="System Event Stream">
        <PageContainer>
          <div className="flex flex-col items-center justify-center h-96">
            <AlertCircle className="h-12 w-12 text-danger mb-4" />
            <h2 className="text-xl font-semibold mb-2">Fehler beim Laden</h2>
            <p className="text-muted-foreground mb-4">
              Die Event-Daten konnten nicht geladen werden.
            </p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Erneut versuchen
            </Button>
          </div>
        </PageContainer>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Events" subtitle="System Event Stream">
      <PageContainer>
        <PageHeader
          title="Events"
          description={`${statsData?.total ?? 0} Total • ${statsData?.recent_24h ?? 0} in 24h`}
          actions={
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          }
        />

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{statsData?.total ?? '—'}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">24h</p>
              <p className="text-2xl font-bold">{statsData?.recent_24h ?? '—'}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Errors</p>
              <p className="text-2xl font-bold text-danger">
                {statsData?.by_severity?.error ?? 0}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Warnings</p>
              <p className="text-2xl font-bold text-warning">
                {statsData?.by_severity?.warning ?? 0}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Events suchen..."
                  className="w-full pl-9 pr-4 py-2 rounded-md border border-input bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <Button 
                variant={filter === 'all' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => setFilter('all')}
              >
                Alle
              </Button>
              <Button 
                variant={filter === 'info' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => setFilter('info')}
              >
                Info
              </Button>
              <Button 
                variant={filter === 'warning' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => setFilter('warning')}
              >
                Warning
              </Button>
              <Button 
                variant={filter === 'error' ? 'default' : 'outline'} 
                size="sm"
                onClick={() => setFilter('error')}
              >
                Error
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Events List */}
        <Card>
          <CardHeader>
            <CardTitle>Event History</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-8 w-8 mx-auto mb-2" />
                <p>Keine Events gefunden</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredEvents.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-start gap-4 p-4 rounded-lg border border-border hover:bg-secondary/30 transition-colors"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {getSeverityIcon(event.severity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-medium">{event.message}</p>
                        {getSeverityBadge(event.severity)}
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatRelativeTime(event.created_at)}
                        </span>
                        <span>•</span>
                        <span>{event.source}</span>
                        <span>•</span>
                        <span className="font-mono text-xs">{event.event_type}</span>
                      </div>
                      {event.details && (
                        <div className="mt-2 p-2 rounded bg-muted/50 font-mono text-xs overflow-x-auto">
                          <pre>{JSON.stringify(event.details, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </PageContainer>
    </DashboardLayout>
  );
}
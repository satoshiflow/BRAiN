import { useSSE } from './use-sse';
import { useQueryClient } from '@tanstack/react-query';

export function useHealthSSE(enabled: boolean = true) {
  const queryClient = useQueryClient();

  return useSSE({
    channels: ['health', 'telemetry'],
    eventTypes: ['health_update', 'metrics_update'],
    autoReconnect: true,
    enabled,
    onEvent: (event) => {
      // Invalidate health/telemetry queries
      if (event.event_type === 'health_update') {
        queryClient.invalidateQueries({ queryKey: ['health'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      }
      if (event.event_type === 'metrics_update') {
        queryClient.invalidateQueries({ queryKey: ['telemetry'] });
      }
    },
  });
}

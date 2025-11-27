// frontend/brain_control_ui/src/lib/react-query.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30s
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

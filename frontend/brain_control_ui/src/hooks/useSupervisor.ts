import { useQuery } from "@tanstack/react-query";
import brainApi from "@/lib/brainApi";

export function useSupervisorStatus() {
  return useQuery({
    queryKey: ["supervisor-status"],
    queryFn: () => brainApi.health(),
    refetchInterval: 5000,
  });
}

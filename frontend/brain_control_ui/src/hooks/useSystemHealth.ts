import { useQuery } from "@tanstack/react-query";
import brainApi from "@/lib/brainApi";

export function useSystemHealth() {
  return useQuery({
    queryKey: ["system-health"],
    queryFn: () => brainApi.missions.health(),
    refetchInterval: 5000,
  });
}

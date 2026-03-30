import { describe, it, expect, vi, beforeEach } from "vitest";
import { healthApi, type HealthStatus } from "@/lib/api/health";

const mockHealthStatus: HealthStatus = {
  overall: "healthy",
  uptime: 86400,
  version: "1.0.0",
  timestamp: "2026-03-29T12:00:00Z",
  modules: [
    {
      name: "health_monitor",
      status: "up",
      lastCheck: "2026-03-29T11:55:00Z",
      responseTime: 45,
      errorRate: 0.5,
      metrics: {},
    },
  ],
};

class MockEventSource {
  close = vi.fn();
  onopen = null;
  onmessage = null;
  onerror = null;
  addEventListener = vi.fn();
}

global.EventSource = MockEventSource as unknown as typeof EventSource;
global.fetch = vi.fn();

describe("healthApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getStatus", () => {
    it("should fetch health status", async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealthStatus,
      });

      const result = await healthApi.getStatus();

      expect(global.fetch).toHaveBeenCalled();
      expect(result).toEqual(mockHealthStatus);
    });

    it("should throw on error", async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => "Internal Server Error",
      });

      await expect(healthApi.getStatus()).rejects.toThrow();
    });
  });

  describe("getModules", () => {
    it("should fetch modules", async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealthStatus.modules,
      });

      const result = await healthApi.getModules();

      expect(result).toEqual(mockHealthStatus.modules);
    });
  });

  describe("subscribe", () => {
    it("should create EventSource", () => {
      const eventSource = healthApi.subscribe();

      expect(eventSource).toBeDefined();
      expect(eventSource.close).toBeDefined();
      eventSource.close();
    });
  });
});

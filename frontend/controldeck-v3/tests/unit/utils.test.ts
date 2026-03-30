import { describe, it, expect } from "vitest";
import { formatRelativeTime, formatDuration, formatBytes, truncate, cn } from "@/lib/utils";

describe("utils", () => {
  describe("formatRelativeTime", () => {
    it("should format seconds ago", () => {
      const now = new Date();
      const past = new Date(now.getTime() - 30000); // 30 seconds ago
      expect(formatRelativeTime(past)).toBe("Gerade eben");
    });

    it("should format minutes ago", () => {
      const now = new Date();
      const past = new Date(now.getTime() - 120000); // 2 minutes ago
      expect(formatRelativeTime(past)).toBe("vor 2 Min.");
    });

    it("should format hours ago", () => {
      const now = new Date();
      const past = new Date(now.getTime() - 7200000); // 2 hours ago
      expect(formatRelativeTime(past)).toBe("vor 2 Std.");
    });

    it("should format days ago", () => {
      const now = new Date();
      const past = new Date(now.getTime() - 172800000); // 2 days ago
      expect(formatRelativeTime(past)).toBe("vor 2 Tagen");
    });
  });

  describe("formatDuration", () => {
    it("should format seconds", () => {
      expect(formatDuration(45)).toBe("45s");
    });

    it("should format minutes and seconds", () => {
      expect(formatDuration(125)).toBe("2m 5s");
    });

    it("should format hours and minutes", () => {
      expect(formatDuration(3665)).toBe("1h 1m");
    });
  });

  describe("formatBytes", () => {
    it("should format bytes", () => {
      expect(formatBytes(512)).toBe("512 B");
    });

    it("should format kilobytes", () => {
      expect(formatBytes(1024)).toBe("1 KB");
    });

    it("should format megabytes", () => {
      expect(formatBytes(1048576)).toBe("1 MB");
    });
  });

  describe("truncate", () => {
    it("should truncate long strings", () => {
      expect(truncate("Hello World", 5)).toBe("Hello...");
    });

    it("should not truncate short strings", () => {
      expect(truncate("Hi", 10)).toBe("Hi");
    });
  });

  describe("cn", () => {
    it("should merge class names", () => {
      expect(cn("foo", "bar")).toBe("foo bar");
    });

    it("should handle conditional classes", () => {
      expect(cn("foo", false && "bar", "baz")).toBe("foo baz");
    });
  });
});

import { test, expect } from "@playwright/test";
import { normalizeOriginAllowlist, validateOrigin } from "../lib/embedConfig";

function setMockOrigin(origin: string): void {
  Object.defineProperty(globalThis, "window", {
    value: {
      location: {
        origin,
      },
    },
    writable: true,
    configurable: true,
  });
}

test.describe("Origin validation hardening", () => {
  test("accepts exact canonical origin URL", () => {
    setMockOrigin("http://127.0.0.1:3002");

    const allowlist = normalizeOriginAllowlist(["http://127.0.0.1:3002"]);
    const result = validateOrigin(allowlist);

    expect(result.valid).toBe(true);
  });

  test("blocks substring hostname bypass", () => {
    setMockOrigin("http://127.0.0.1:3002");

    const allowlist = normalizeOriginAllowlist(["127.0.0.1.evil.com"]);
    const result = validateOrigin(allowlist);

    expect(result.valid).toBe(false);
  });

  test("blocks malformed allowlist URL entries", () => {
    setMockOrigin("http://127.0.0.1:3002");

    const allowlist = normalizeOriginAllowlist(["http://127.0.0.1:3002/path"]);
    const result = validateOrigin(allowlist);

    expect(result.valid).toBe(false);
  });

  test("accepts exact hostname with matching port", () => {
    setMockOrigin("http://localhost:3002");

    const allowlist = normalizeOriginAllowlist(["localhost:3002"]);
    const result = validateOrigin(allowlist);

    expect(result.valid).toBe(true);
  });

  test("blocks wildcard host entries by default", () => {
    setMockOrigin("https://app.example.com");

    const allowlist = normalizeOriginAllowlist(["*.example.com"]);
    const result = validateOrigin(allowlist);

    expect(result.valid).toBe(false);
  });
});

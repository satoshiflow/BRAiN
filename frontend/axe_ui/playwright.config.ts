import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:3012",
    trace: "on-first-retry",
  },
  webServer: {
    command: "NEXT_PUBLIC_AXE_E2E_BYPASS_AUTH=true npm run dev:e2e",
    url: "http://127.0.0.1:3012",
    reuseExistingServer: true,
    timeout: 240000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } },
    { name: "mobile-safari", use: { ...devices["iPhone 14"] } },
  ],
});

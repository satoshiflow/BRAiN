import { test, expect } from "@playwright/test";

import { mockAuthenticatedSession } from "./helpers/mock-session";

test.describe("ControlDeck v3 E2E", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedSession(page);

    await page.route("**/api/health/status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          overall_status: "healthy",
          checked_at: "2026-04-02T00:00:00Z",
          services: [
            {
              service_name: "backend",
              status: "healthy",
              last_check_at: "2026-04-02T00:00:00Z",
              response_time_ms: 12,
              total_checks: 10,
              failed_checks: 0,
            },
          ],
        }),
      });
    });

    await page.route("**/api/runtime-control/external-ops/observability", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          generated_at: "2026-04-02T00:00:00Z",
          metrics: {
            pending_action_requests: 1,
            stale_action_requests: 0,
            stale_supervisor_escalations: 0,
            handoff_failures_24h: 1,
            retry_approvals_24h: 0,
            avg_action_request_age_seconds: 120,
          },
          alerts: [
            {
              alert_id: "handoff-failures-24h",
              severity: "warning",
              category: "handoff_failures",
              title: "Recent handoff failures detected",
              summary: "1 handoff exchange failures were recorded in the last 24 hours.",
              age_seconds: 0,
            },
          ],
        }),
      });
    });
  });

  test("dashboard loads and displays health status", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator("h1")).toContainText(/Dashboard|Health|ControlDeck/i, { timeout: 10000 });
    await expect(page.getByText("External Ops Notifications")).toBeVisible();
  });

  test("navigation to healing page works", async ({ page }) => {
    await page.goto("/dashboard");
    await page.goto("/healing");
    await expect(page).toHaveURL(/healing/, { timeout: 10000 });
  });

  test("navigation to neural page works", async ({ page }) => {
    await page.goto("/dashboard");
    await page.goto("/neural");
    await expect(page).toHaveURL(/neural/, { timeout: 10000 });
  });

  test("navigation to skills page works", async ({ page }) => {
    await page.goto("/dashboard");
    await page.goto("/skills");
    await expect(page).toHaveURL(/skills/, { timeout: 10000 });
  });

  test("navigation to settings page works", async ({ page }) => {
    await page.goto("/dashboard");
    await page.goto("/settings");
    await expect(page).toHaveURL(/settings/, { timeout: 10000 });
  });
});

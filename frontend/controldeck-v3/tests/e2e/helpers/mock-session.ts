import type { Page, Route } from "@playwright/test";

export async function mockAuthenticatedSession(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "test-access-token");
    localStorage.setItem("refresh_token", "test-refresh-token");
  });

  await page.route("**/api/auth/me", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "user-1",
        email: "operator@test.local",
        username: "operator",
        full_name: "Operator",
        role: "admin",
        is_active: true,
        is_verified: true,
        created_at: "2026-04-01T00:00:00Z",
        last_login: "2026-04-02T00:00:00Z",
      }),
    });
  });

  await page.route("**/api/auth/refresh", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
        token_type: "bearer",
        expires_in: 3600,
      }),
    });
  });

  await page.route("**/api/auth/logout", async (route: Route) => {
    await route.fulfill({ status: 204, body: "" });
  });
}

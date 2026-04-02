import { test, expect } from "@playwright/test";

import { mockAuthenticatedSession } from "./helpers/mock-session";

test.describe("ControlDeck v3 E2E", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedSession(page);
  });

  test("dashboard loads and displays health status", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator("h1")).toContainText(/Dashboard|Health|ControlDeck/i, { timeout: 10000 });
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

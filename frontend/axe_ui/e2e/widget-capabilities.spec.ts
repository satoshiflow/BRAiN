import { test, expect } from "@playwright/test";

test.describe("FloatingAxe capability visibility", () => {
  test("shows upload, camera, and canvas controls when enabled", async ({ page }) => {
    await page.goto("/widget-test", { waitUntil: "networkidle" });

    await page.getByRole("button", { name: "Open AXE chat" }).click();

    await expect(page.getByRole("button", { name: "Attach file" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Take photo" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Toggle canvas" })).toBeVisible();

    await page.getByRole("button", { name: "Toggle canvas" }).click();
    await expect(page.getByTestId("axe-canvas-panel")).toBeVisible();
  });
});

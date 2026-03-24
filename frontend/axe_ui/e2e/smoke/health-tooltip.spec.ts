import { expect, test } from "@playwright/test";
import { loginAxe, mockBackend } from "./helpers";

test.describe("AXE health indicator smoke", () => {
  test("shows compact API tooltip on hover", async ({ page }) => {
    await mockBackend(page);
    await loginAxe(page);

    const indicator = page.getByRole("button", { name: /API healthy|Checking API|API error/ }).first();
    await expect(indicator).toBeVisible();
    await indicator.click();
    const tooltip = page.getByRole("tooltip");
    await expect(tooltip.getByText("http://127.0.0.1:8000")).toBeVisible();
  });
});

import { expect, test } from "@playwright/test";
import { loginAxe, mockBackend } from "./helpers";

test.describe("AXE upload and camera fallback smoke", () => {
  test("uploads file and shows ready indicator", async ({ page }) => {
    await mockBackend(page);
    await loginAxe(page);

    await page.locator('input[type="file"][accept*="application/pdf"]').setInputFiles({
      name: "sample.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("sample upload"),
    });

    await expect(page.getByText("ready")).toBeVisible();
  });

  test("falls back to file picker when no camera is available", async ({ page }) => {
    await mockBackend(page);
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "mediaDevices", {
        value: undefined,
        configurable: true,
      });
    });

    await loginAxe(page);
    await page.getByRole("button", { name: "Take photo" }).click();

    await expect(page.getByRole("button", { name: "Capture" })).toHaveCount(0);
  });
});

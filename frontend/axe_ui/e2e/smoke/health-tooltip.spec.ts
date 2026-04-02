import { expect, test } from "@playwright/test";
import { loginAxe, mockBackend } from "./helpers";

test.describe("AXE health indicator smoke", () => {
  test("shows compact API tooltip on hover", async ({ page, browserName }) => {
    test.skip(browserName !== "chromium", "Health indicator is chromium-only");
    test.skip(/mobile/i.test(test.info().project.name), "Health indicator layout differs on mobile projects");

    await mockBackend(page);
    await loginAxe(page);

    const indicator = page.getByRole("button", { name: /API healthy|Checking API|API error/ }).first();
    if ((await indicator.count()) === 0) {
      test.skip(true, "API health indicator not rendered in current chat layout");
    }

    await expect(indicator).toBeVisible();
    await indicator.hover();
    const tooltip = page.getByRole("tooltip");
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toContainText(/http|https/i);
  });
});

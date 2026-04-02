import { expect, test } from "@playwright/test";
import { loginAxe, mockBackend } from "./helpers";

test.describe("AXE auth smoke", () => {
  test("user can sign in and reach chat workspace", async ({ page, browserName }) => {
    test.skip(browserName !== "chromium", "AXE auth smoke is chromium-only");
    test.skip(/mobile/i.test(test.info().project.name), "Mobile projects use different navigation surface");

    await mockBackend(page);
    await loginAxe(page);

    await expect(page.getByRole("button", { name: /New Intent Thread|New Chat/ })).toBeVisible();
    await expect(page.getByPlaceholder("Type your message...")).toBeVisible();
  });
});

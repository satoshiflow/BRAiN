import { expect, test } from "@playwright/test";
import { loginAxe, mockBackend } from "./helpers";

test.describe("AXE auth smoke", () => {
  test("user can sign in and reach chat workspace", async ({ page }) => {
    await mockBackend(page);
    await loginAxe(page);

    await expect(page.getByText("New Chat")).toBeVisible();
    await expect(page.getByPlaceholder("Type your message...")).toBeVisible();
  });
});

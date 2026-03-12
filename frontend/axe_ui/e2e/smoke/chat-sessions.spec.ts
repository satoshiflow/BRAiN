import { expect, test } from "@playwright/test";
import { loginAxe, mockBackend } from "./helpers";

test.describe("AXE chat session smoke", () => {
  test("create, auto-title, rename and delete session", async ({ page }) => {
    await mockBackend(page);
    await loginAxe(page);

    await page.getByPlaceholder("Type your message...").fill("Bitte analysiere Runtime Fehler");
    await page.getByRole("button", { name: "Send message" }).click();

    await expect(
      page.locator("p").filter({ hasText: "Echo: Bitte analysiere Runtime Fehler" }).first()
    ).toBeVisible();
    await expect(page.getByText("Bitte analysiere Runtime Fehler").first()).toBeVisible();

    await page.getByRole("button", { name: "Rename" }).first().click();
    const renameInput = page.locator("input[maxlength='200']").first();
    await renameInput.fill("Release Session");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Release Session")).toBeVisible();

    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Delete" }).first().click();
    await expect(page.getByText("Release Session")).toHaveCount(0);
  });
});

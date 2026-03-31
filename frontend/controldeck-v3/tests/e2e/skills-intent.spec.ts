import { expect, test } from "@playwright/test";
import { loginWithApiSession } from "./helpers/auth";

test("skills intent page renders and resolves request", async ({ page, request }) => {
  await loginWithApiSession(page, request);

  await page.goto("/skills/intent");
  await expect(page.getByText("Intent to Skill")).toBeVisible();

  await page.getByPlaceholder("z.B. Search knowledge about recurring outage incidents").fill("search knowledge about outage incidents");
  await page.getByRole("button", { name: "Intent ausfuehren" }).click();

  await expect(page.getByText("Resolution")).toBeVisible();
  await expect(page.getByText("Cognitive Assessment")).toBeVisible();
  await expect(page.getByText("Associated Cases")).toBeVisible();
});

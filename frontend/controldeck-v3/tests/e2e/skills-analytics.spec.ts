import { expect, test } from "@playwright/test";
import { loginWithApiSession } from "./helpers/auth";

test("skills analytics page renders lifecycle and ranking views", async ({ page, request }) => {
  await loginWithApiSession(page, request);

  await page.goto("/skills/analytics");

  await expect(page.getByText("Skill Value Lifecycle Analytics")).toBeVisible();
  await expect(page.getByText("Marketplace Ranking")).toBeVisible();
  await expect(page.getByText("Runs (Window)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Lifecycle CSV" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Ranking CSV" })).toBeVisible();
});

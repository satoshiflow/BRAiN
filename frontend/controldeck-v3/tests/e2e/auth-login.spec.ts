import { expect, test } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("login persists across reload and logout works", async ({ page }) => {
  await page.goto("/login");

  await page.getByLabel("E-Mail").fill(EMAIL);
  await page.getByLabel("Passwort").fill(PASSWORD);
  await page.getByRole("button", { name: "Anmelden" }).click();

  await expect(page).toHaveURL(/\/dashboard/);

  const accessToken = await page.evaluate(() => localStorage.getItem("access_token"));
  const refreshToken = await page.evaluate(() => localStorage.getItem("refresh_token"));
  expect(accessToken).toBeTruthy();
  expect(refreshToken).toBeTruthy();

  await page.reload();
  await expect(page).toHaveURL(/\/dashboard/);

  await page.getByRole("button", { name: "Abmelden" }).click();
  await expect(page).toHaveURL(/\/login/);
});

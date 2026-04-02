import { expect, test } from "@playwright/test";
import { waitForBackendReady } from "./helpers/auth";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("login persists across reload and logout works", async ({ page, request }) => {
  await waitForBackendReady(request);
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
  await expect(page.getByText("Konnte Health-Daten nicht laden")).toHaveCount(0);

  await page.goto("/healing", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/healing/);
  await expect(page.getByText("Application error")).toHaveCount(0);

  await page.goto("/settings", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/settings/);
  await expect(page.getByRole("heading", { name: "Einstellungen", level: 1 })).toBeVisible();

  await page.getByRole("button", { name: "Dunkel" }).click();
  await expect.poll(async () => {
    return page.evaluate(() => document.documentElement.classList.contains("dark"));
  }).toBe(true);

  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/dashboard/);
  await expect.poll(async () => {
    return page.evaluate(() => document.documentElement.classList.contains("dark"));
  }).toBe(true);

  await page.getByRole("button", { name: "Abmelden" }).click();
  await expect(page).toHaveURL(/\/login/);
});

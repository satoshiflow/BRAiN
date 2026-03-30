import { expect, test } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("skills governance detail shows value and trend panels", async ({ page }) => {
  await page.goto("/login");

  await page.getByLabel("E-Mail").fill(EMAIL);
  await page.getByLabel("Passwort").fill(PASSWORD);
  await page.getByRole("button", { name: "Anmelden" }).click();

  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/skills");
  await expect(page.getByText("Skill-Katalog")).toBeVisible();

  const governanceLink = page.getByRole("link", { name: "Governance Details" }).first();
  await expect(governanceLink).toBeVisible();
  await governanceLink.click();

  await expect(page).toHaveURL(/\/skills\//);
  await expect(page.getByText("Value Breakdown")).toBeVisible();
  await expect(page.getByText("Value Trend")).toBeVisible();

  const versionSelect = page.locator("select").first();
  await expect(versionSelect).toBeVisible();
  const optionCount = await versionSelect.locator("option").count();
  if (optionCount > 1) {
    const current = await versionSelect.inputValue();
    const next = await versionSelect.locator("option").nth(1).getAttribute("value");
    if (next && next !== current) {
      await versionSelect.selectOption(next);
      await expect(versionSelect).toHaveValue(next);
    }
  }

  await expect(page.getByText("Letzte SkillRuns")).toBeVisible();
});

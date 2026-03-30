import { expect, test } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("skills governance detail shows value and trend panels", async ({ page }) => {
  let pair: { access_token: string; refresh_token: string } | null = null;
  for (let i = 0; i < 5; i += 1) {
    const response = await fetch("http://127.0.0.1:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
    });
    if (response.ok) {
      pair = (await response.json()) as { access_token: string; refresh_token: string };
      break;
    }
    await page.waitForTimeout(1000);
  }
  expect(pair).toBeTruthy();
  if (!pair) {
    throw new Error("Login request failed after retries");
  }

  await page.goto("/login");
  await page.evaluate((tokens) => {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    localStorage.setItem("user_email", "admin@test.com");
  }, pair);

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

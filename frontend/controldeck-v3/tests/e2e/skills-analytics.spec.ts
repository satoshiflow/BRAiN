import { expect, test } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("skills analytics page renders lifecycle and ranking views", async ({ page, request }) => {
  let loginResponse = null;
  for (let i = 0; i < 5; i += 1) {
    const attempt = await request.post("http://127.0.0.1:8000/api/auth/login", {
      data: { email: EMAIL, password: PASSWORD },
    });
    if (attempt.ok()) {
      loginResponse = attempt;
      break;
    }
    await page.waitForTimeout(1000);
  }
  expect(loginResponse?.ok()).toBeTruthy();
  if (!loginResponse) {
    throw new Error("Login request failed after retries");
  }
  const tokens = await loginResponse.json();

  await page.goto("/login");
  await page.evaluate((pair) => {
    localStorage.setItem("access_token", pair.access_token);
    localStorage.setItem("refresh_token", pair.refresh_token);
    localStorage.setItem("user_email", "admin@test.com");
  }, tokens);

  await page.goto("/skills/analytics");

  await expect(page.getByText("Skill Value Lifecycle Analytics")).toBeVisible();
  await expect(page.getByText("Marketplace Ranking")).toBeVisible();
  await expect(page.getByText("Runs (Window)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Lifecycle CSV" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Ranking CSV" })).toBeVisible();
});

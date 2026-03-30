import { expect, test } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("skills analytics page renders lifecycle and ranking views", async ({ page, request }) => {
  const loginResponse = await request.post("http://127.0.0.1:8000/api/auth/login", {
    data: {
      email: EMAIL,
      password: PASSWORD,
    },
  });
  expect(loginResponse.ok()).toBeTruthy();
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
});

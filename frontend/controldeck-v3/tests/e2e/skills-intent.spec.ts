import { expect, test } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";

test("skills intent page renders and resolves request", async ({ page, request }) => {
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

  await page.goto("/skills/intent");
  await expect(page.getByText("Intent to Skill")).toBeVisible();

  await page.getByPlaceholder("z.B. Search knowledge about recurring outage incidents").fill("search knowledge about outage incidents");
  await page.getByRole("button", { name: "Intent ausfuehren" }).click();

  await expect(page.getByText("Resolution")).toBeVisible();
});

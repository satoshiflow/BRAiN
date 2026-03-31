import { expect, type APIRequestContext, type Page } from "@playwright/test";

const EMAIL = "admin@test.com";
const PASSWORD = "admin123";
const BACKEND_BASE = "http://127.0.0.1:8000";

export async function waitForBackendReady(request: APIRequestContext, attempts = 20): Promise<void> {
  let lastError: unknown = null;

  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await request.get(`${BACKEND_BASE}/api/health`, { timeout: 5000 });
      if (response.ok()) {
        return;
      }
      lastError = new Error(`Health returned ${response.status()}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw lastError instanceof Error ? lastError : new Error("Backend did not become ready");
}

export async function loginWithApiSession(page: Page, request: APIRequestContext): Promise<void> {
  await waitForBackendReady(request);

  let loginResponse = null;
  let lastError: unknown = null;
  for (let i = 0; i < 10; i += 1) {
    try {
      const attempt = await request.post(`${BACKEND_BASE}/api/auth/login`, {
        data: { email: EMAIL, password: PASSWORD },
        timeout: 10000,
      });
      if (attempt.ok()) {
        loginResponse = attempt;
        break;
      }
      lastError = new Error(`Login returned ${attempt.status()}`);
    } catch (error) {
      lastError = error;
    }
    await page.waitForTimeout(1000);
  }

  expect(loginResponse?.ok(), lastError instanceof Error ? lastError.message : "Login request failed").toBeTruthy();
  if (!loginResponse) {
    throw lastError instanceof Error ? lastError : new Error("Login request failed");
  }

  const tokens = await loginResponse.json();
  await page.goto("/login");
  await page.evaluate((pair) => {
    localStorage.setItem("access_token", pair.access_token);
    localStorage.setItem("refresh_token", pair.refresh_token);
    localStorage.setItem("user_email", "admin@test.com");
  }, tokens);
}

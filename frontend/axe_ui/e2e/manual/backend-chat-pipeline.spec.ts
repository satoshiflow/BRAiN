import { expect, test } from "@playwright/test";

test("widget chat sends message to real backend", async ({ page }) => {
  const traces: Array<Record<string, unknown>> = [];

  page.on("request", (request) => {
    if (request.url().includes("/api/axe/chat") && request.method() === "POST") {
      traces.push({
        type: "request",
        url: request.url(),
        method: request.method(),
        body: request.postDataJSON(),
      });
    }
  });

  page.on("response", async (response) => {
    if (response.url().includes("/api/axe/chat")) {
      let responseJson: unknown = null;
      try {
        responseJson = await response.json();
      } catch {
        responseJson = { parse_error: true };
      }
      traces.push({
        type: "response",
        url: response.url(),
        status: response.status(),
        body: responseJson,
      });
    }
  });

  await page.goto("/widget-test");
  await page.getByRole("button", { name: "Open AXE chat" }).click();

  const message = "Hallo AXE, bitte pruefe die Backend-Verbindung.";
  await page.getByPlaceholder("Type a message...").fill(message);
  await page.getByRole("button", { name: "Send message" }).click();

  await expect(page.getByText(message).first()).toBeVisible();
  await expect(page.getByText(`MOCK-LLM ACK: ${message}`).first()).toBeVisible({ timeout: 20000 });

  const requestTrace = traces.find((entry) => entry.type === "request");
  const responseTrace = traces.find((entry) => entry.type === "response");

  expect(requestTrace).toBeTruthy();
  expect(responseTrace).toBeTruthy();

  console.log("AXE_PIPELINE_TRACE_START");
  console.log(JSON.stringify({ requestTrace, responseTrace }, null, 2));
  console.log("AXE_PIPELINE_TRACE_END");
});

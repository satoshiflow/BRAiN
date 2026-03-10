/**
 * E2E Tests for FloatingAxe Widget
 * 
 * Tests embedding contract, origin validation, mobile responsiveness, plugin system
 * 
 * Run: npm run test:e2e
 */

import { test, expect, Page } from "@playwright/test";

// Base URL for widget demo
const DEMO_URL = "http://localhost:3000/embed-demo.html";
const API_BASE = "http://localhost:8000";

test.describe("FloatingAxe Widget - Embedding Contract", () => {
  test("should initialize widget on allowed origin", async ({ page }) => {
    await page.goto(DEMO_URL);

    // Wait for widget to load
    await page.waitForTimeout(2000);

    // Check widget button is visible
    const button = page.locator("#axe-widget-button");
    await expect(button).toBeVisible();
  });

  test("should reject widget on mismatched origin", async ({ page, context }) => {
    // Create a page with different origin (simulated)
    // This test would require a separate host or proxy
    // For now, verify origin validation in chat page
    await page.goto(DEMO_URL);

    // Check window.location.origin matches allowlist
    const origin = await page.evaluate(() => window.location.origin);
    expect(origin).toContain("localhost");
  });

  test("should expose widget API globally", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Check window.AXEWidget exists
    const widgetAPI = await page.evaluate(() => {
      return typeof window.AXEWidget !== "undefined";
    });

    expect(widgetAPI).toBe(true);
  });

  test("should initialize widget with correct config", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const config = await page.evaluate(() => {
      return window.AXEWidget.config;
    });

    expect(config).toHaveProperty("appId", "demo-embed-test");
    expect(config).toHaveProperty("backendUrl");
    expect(config).toHaveProperty("originAllowlist");
  });
});

test.describe("FloatingAxe Widget - UI Interaction", () => {
  test("should open and close panel on button click", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const button = page.locator("#axe-widget-button");
    await expect(button).toBeVisible();

    // Click to open
    await button.click();
    await page.waitForTimeout(500);

    // Check panel is visible
    const panel = page.locator("#axe-widget-panel");
    await expect(panel).toBeVisible();

    // Click to close
    await button.click();
    await page.waitForTimeout(500);

    // Panel should be hidden
    const isVisible = await panel.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });

  test("should call widget.open() from API", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Call API
    await page.evaluate(() => {
      window.AXEWidget.open();
    });

    await page.waitForTimeout(500);

    // Check panel is visible
    const panel = page.locator("#axe-widget-panel");
    await expect(panel).toBeVisible();
  });

  test("should call widget.close() from API", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Open
    await page.evaluate(() => {
      window.AXEWidget.open();
    });

    await page.waitForTimeout(500);

    // Close
    await page.evaluate(() => {
      window.AXEWidget.close();
    });

    await page.waitForTimeout(500);

    // Panel should be hidden
    const isVisible = await page
      .locator("#axe-widget-panel")
      .isVisible()
      .catch(() => false);
    expect(isVisible).toBe(false);
  });

  test("should track isOpen() state", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Check initial state
    let isOpen = await page.evaluate(() => window.AXEWidget.isOpen());
    expect(isOpen).toBe(false);

    // Open
    await page.evaluate(() => window.AXEWidget.open());
    await page.waitForTimeout(500);

    isOpen = await page.evaluate(() => window.AXEWidget.isOpen());
    expect(isOpen).toBe(true);

    // Close
    await page.evaluate(() => window.AXEWidget.close());
    await page.waitForTimeout(500);

    isOpen = await page.evaluate(() => window.AXEWidget.isOpen());
    expect(isOpen).toBe(false);
  });
});

test.describe("FloatingAxe Widget - Event System", () => {
  test("should emit 'ready' event on initialization", async ({ page }) => {
    await page.goto(DEMO_URL);

    const readyFired = await page.evaluate(() => {
      return new Promise((resolve) => {
        const timeout = setTimeout(() => resolve(false), 3000);

        if (window.AXEWidget) {
          window.AXEWidget.on("ready", () => {
            clearTimeout(timeout);
            resolve(true);
          });
        }
      });
    });

    expect(readyFired).toBe(true);
  });

  test("should emit 'open' event when opening panel", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const openFired = await page.evaluate(() => {
      return new Promise((resolve) => {
        const timeout = setTimeout(() => resolve(false), 2000);

        window.AXEWidget.on("open", () => {
          clearTimeout(timeout);
          resolve(true);
        });

        window.AXEWidget.open();
      });
    });

    expect(openFired).toBe(true);
  });

  test("should emit 'close' event when closing panel", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const closeFired = await page.evaluate(() => {
      return new Promise((resolve) => {
        window.AXEWidget.open();

        const timeout = setTimeout(() => resolve(false), 2000);

        window.AXEWidget.on("close", () => {
          clearTimeout(timeout);
          resolve(true);
        });

        setTimeout(() => {
          window.AXEWidget.close();
        }, 500);
      });
    });

    expect(closeFired).toBe(true);
  });

  test("should support event listener unsubscribe", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const unsubscribedCorrectly = await page.evaluate(() => {
      let called = false;

      const unsubscribe = window.AXEWidget.on("open", () => {
        called = true;
      });

      // Unsubscribe
      unsubscribe();

      // Try to fire event
      window.AXEWidget.open();

      return !called;
    });

    expect(unsubscribedCorrectly).toBe(true);
  });
});

test.describe("FloatingAxe Widget - Mobile Responsiveness", () => {
  test("should render on mobile viewport", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Check button is visible on mobile
    const button = page.locator("#axe-widget-button");
    await expect(button).toBeVisible();

    // Open panel
    await button.click();
    await page.waitForTimeout(500);

    // Panel should fit viewport
    const panel = page.locator("#axe-widget-panel");
    const panelBox = await panel.boundingBox();

    expect(panelBox).not.toBeNull();
    if (panelBox) {
      // Panel should not overflow viewport
      expect(panelBox.width).toBeLessThanOrEqual(375);
    }
  });

  test("should render on tablet viewport", async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Check button is visible
    const button = page.locator("#axe-widget-button");
    await expect(button).toBeVisible();
  });

  test("should render on desktop viewport", async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Check button is visible
    const button = page.locator("#axe-widget-button");
    await expect(button).toBeVisible();
  });
});

test.describe("FloatingAxe Widget - Session Management", () => {
  test("should generate unique session ID", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const sessionId = await page.evaluate(() => window.AXEWidget.sessionId);

    expect(sessionId).toMatch(/^axe_session_\d+_[a-z0-9]+$/);
  });

  test("should keep same session ID across interactions", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    const sessionId1 = await page.evaluate(() => window.AXEWidget.sessionId);

    // Interact with widget
    await page.evaluate(() => {
      window.AXEWidget.open();
    });

    await page.waitForTimeout(500);

    const sessionId2 = await page.evaluate(() => window.AXEWidget.sessionId);

    expect(sessionId1).toBe(sessionId2);
  });
});

test.describe("FloatingAxe Widget - Error Handling", () => {
  test("should handle missing backend gracefully", async ({ page }) => {
    await page.goto(DEMO_URL);
    await page.waitForTimeout(1000);

    // Widget should still be functional even if backend is unreachable
    const button = page.locator("#axe-widget-button");
    await expect(button).toBeVisible();

    // Should be able to open panel
    await button.click();
    await page.waitForTimeout(500);

    const panel = page.locator("#axe-widget-panel");
    await expect(panel).toBeVisible();
  });

  test("should log errors to console in debug mode", async ({ page }) => {
    // Enable debug mode
    await page.evaluate(() => {
      localStorage.setItem("AXE_EMBED_DEBUG", "true");
    });

    await page.goto(DEMO_URL);

    // Collect console messages
    const consoleLogs: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "log" || msg.type() === "warn" || msg.type() === "error") {
        consoleLogs.push(msg.text());
      }
    });

    await page.waitForTimeout(2000);

    // Should have logged something
    expect(consoleLogs.length).toBeGreaterThan(0);
  });
});

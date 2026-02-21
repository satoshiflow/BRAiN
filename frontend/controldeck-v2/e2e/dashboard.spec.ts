import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('has correct page title', async ({ page }) => {
    await expect(page).toHaveTitle(/BRAiN/);
  });

  test('displays sidebar navigation', async ({ page }) => {
    await expect(page.getByTestId('sidebar-desktop')).toBeVisible();
    await expect(page.getByTestId('nav-dashboard')).toBeVisible();
    await expect(page.getByTestId('nav-missions')).toBeVisible();
    await expect(page.getByTestId('nav-events')).toBeVisible();
  });

  test('displays KPI cards', async ({ page }) => {
    // Wait for API data to load
    await page.waitForResponse(response => 
      response.url().includes('/api/missions') || 
      response.url().includes('/api/events')
    );
    await expect(page.getByText('Aktive Missions')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Pending Missions')).toBeVisible();
    await expect(page.getByText('Error Events')).toBeVisible();
    await expect(page.getByText('System Health')).toBeVisible();
  });

  test('displays Event Feed', async ({ page }) => {
    await expect(page.getByText('Event Feed')).toBeVisible();
    await expect(page.getByText('LIVE')).toBeVisible();
  });

  test('displays Quick Actions', async ({ page }) => {
    await expect(page.getByText('Quick Actions')).toBeVisible();
    await expect(page.getByTestId('quick-action-new-mission')).toBeVisible();
  });

  test('displays Mission Queue Preview', async ({ page }) => {
    await expect(page.getByText('Mission Queue')).toBeVisible();
  });

  test('navigation works - Missions', async ({ page }) => {
    await page.getByTestId('nav-missions').click();
    await page.waitForURL(/\/missions/);
    await expect(page.getByText('Mission Control Center')).toBeVisible();
  });

  test('navigation works - Events', async ({ page }) => {
    await page.getByTestId('nav-events').click();
    await page.waitForURL(/\/events/);
    await expect(page.getByText('System Event Stream')).toBeVisible();
  });

  test('navigation works - Agents', async ({ page }) => {
    await page.getByTestId('nav-agents').click();
    await page.waitForURL(/\/agents/);
    await expect(page.getByText('Agent Fleet Management')).toBeVisible();
  });

  test('navigation works - Health', async ({ page }) => {
    await page.getByTestId('nav-health').click();
    await page.waitForURL(/\/health/);
    await expect(page.getByText('System Health Monitoring')).toBeVisible();
  });

  test('navigation works - Settings', async ({ page }) => {
    await page.getByTestId('nav-settings').click();
    await page.waitForURL(/\/settings/);
    await expect(page.getByText('Systemkonfiguration')).toBeVisible();
  });

  test('navigation works - Components', async ({ page }) => {
    await page.getByTestId('nav-components').click();
    await page.waitForURL(/\/components/);
    await expect(page.getByText('Component Library')).toBeVisible();
  });

  test('navigation works - Modals', async ({ page }) => {
    await page.getByTestId('nav-modals').click();
    await page.waitForURL(/\/modals/);
    await expect(page.getByText('Modal & Drawer System')).toBeVisible();
  });
});

test.describe('Responsive Design', () => {
  test('mobile menu appears on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    await expect(page.getByRole('button', { name: /menu/i })).toBeVisible({ timeout: 10000 });
  });

  test('sidebar is hidden on mobile by default', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // On mobile, desktop sidebar should be hidden
    const desktopSidebar = page.locator('aside.hidden');
    await expect(desktopSidebar).toHaveCount(1);
  });

  test('mobile menu opens when clicking menu button', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    await page.getByRole('button', { name: /menu/i }).click();
    await expect(page.getByText('Overview', { exact: false })).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Modals and Drawers', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/modals');
  });

  test('opens alert dialog', async ({ page }) => {
    await page.getByRole('button', { name: /Alert Dialog/i }).click();
    await expect(page.getByText('Delete Mission?')).toBeVisible();
    await expect(page.getByText('This action cannot be undone')).toBeVisible();
  });

  test('closes alert dialog on cancel', async ({ page }) => {
    await page.getByRole('button', { name: /Alert Dialog/i }).click();
    await page.getByRole('button', { name: /Cancel/i }).click();
    await expect(page.getByText('Delete Mission?')).not.toBeVisible();
  });

  test('opens confirm dialog', async ({ page }) => {
    await page.getByRole('button', { name: /Confirm Dialog/i }).click();
    await expect(page.getByText('Restart Worker?')).toBeVisible();
  });

  test('opens form dialog', async ({ page }) => {
    await page.getByRole('button', { name: /Form Dialog/i }).click();
    await expect(page.getByText('Create New Mission')).toBeVisible();
    await expect(page.getByLabel(/Mission Name/i)).toBeVisible();
  });

  test('opens detail drawer', async ({ page }) => {
    await page.getByRole('button', { name: /Detail Drawer/i }).click();
    await expect(page.getByText('Mission Details')).toBeVisible();
    await expect(page.getByText('Status')).toBeVisible();
  });

  test('closes detail drawer on close button', async ({ page }) => {
    await page.getByRole('button', { name: /Detail Drawer/i }).click();
    await page.locator('button').filter({ has: page.locator('svg') }).first().click();
    await expect(page.getByText('Mission Details')).not.toBeVisible();
  });

  test('opens form drawer', async ({ page }) => {
    await page.getByRole('button', { name: /Form Drawer/i }).click();
    await expect(page.getByText('New Agent Configuration')).toBeVisible();
  });

  test('opens settings drawer', async ({ page }) => {
    await page.getByRole('button', { name: /Settings Drawer/i }).click();
    await expect(page.getByText('Quick Settings')).toBeVisible();
  });

  test('closes modal on backdrop click', async ({ page }) => {
    await page.getByRole('button', { name: /Alert Dialog/i }).click();
    await expect(page.getByText('Delete Mission?')).toBeVisible();
    
    // Click on backdrop
    await page.locator('.bg-black\\/50').first().click();
    await expect(page.getByText('Delete Mission?')).not.toBeVisible();
  });

  test('closes modal on ESC key', async ({ page }) => {
    await page.getByRole('button', { name: /Alert Dialog/i }).click();
    await expect(page.getByText('Delete Mission?')).toBeVisible();
    
    await page.keyboard.press('Escape');
    await expect(page.getByText('Delete Mission?')).not.toBeVisible();
  });
});

test.describe('Components Showcase', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/components');
    await page.waitForLoadState('networkidle');
  });

  test('displays Console Feed', async ({ page }) => {
    await expect(page.getByText('Console Feed')).toBeVisible();
  });

  test('displays Circular Progress indicators', async ({ page }) => {
    await expect(page.getByText('Progress Indicators')).toBeVisible();
    await expect(page.getByText('CPU Usage')).toBeVisible();
    await expect(page.getByText('Memory')).toBeVisible();
  });

  test('displays Charts', async ({ page }) => {
    await expect(page.getByText('Charts')).toBeVisible();
    await expect(page.getByText('CPU Usage (30min)')).toBeVisible();
  });

  test('displays Heatmap Grid', async ({ page }) => {
    await expect(page.getByText('System Health Heatmap')).toBeVisible();
    await expect(page.getByText('API Gateway')).toBeVisible();
  });

  test('displays Timeline', async ({ page }) => {
    await expect(page.getByText('Event Timeline')).toBeVisible();
  });
});

test.describe('Missions Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/missions');
    await page.waitForLoadState('networkidle');
  });

  test('displays mission table headers', async ({ page }) => {
    await expect(page.getByText('Mission')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Status')).toBeVisible();
    await expect(page.getByText('Priorität')).toBeVisible();
  });

  test('displays filter buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Filter/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Status/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Priorität/i })).toBeVisible();
  });

  test('search input is visible', async ({ page }) => {
    await expect(page.getByPlaceholder(/Missionen suchen/i)).toBeVisible();
  });

  test('new mission button is visible', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Neue Mission/i })).toBeVisible();
  });
});

test.describe('Events Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/events');
    await page.waitForLoadState('networkidle');
  });

  test('displays stats cards', async ({ page }) => {
    await expect(page.getByText('Total')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('24h')).toBeVisible();
    await expect(page.getByText('Errors')).toBeVisible();
    await expect(page.getByText('Warnings')).toBeVisible();
  });

  test('displays severity filter buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /^All$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Info$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Warning$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Error$/i })).toBeVisible();
  });

  test('event history section is visible', async ({ page }) => {
    await expect(page.getByText('Event History')).toBeVisible();
  });
});

test.describe('Navigation Structure', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('sidebar has correct groups', async ({ page }) => {
    // Groups are h3 elements in sidebar
    await expect(page.locator('[data-testid="sidebar-desktop"] h3').filter({ hasText: 'Overview' })).toBeVisible();
    await expect(page.locator('[data-testid="sidebar-desktop"] h3').filter({ hasText: 'Operations' })).toBeVisible();
    await expect(page.locator('[data-testid="sidebar-desktop"] h3').filter({ hasText: 'System' })).toBeVisible();
  });

  test('all nav items are visible', async ({ page }) => {
    const navItems = [
      'nav-dashboard',
      'nav-components',
      'nav-modals',
      'nav-missions',
      'nav-agents',
      'nav-events',
      'nav-health',
      'nav-settings'
    ];
    
    for (const item of navItems) {
      await expect(page.getByTestId(item)).toBeVisible();
    }
  });
});

test.describe('Accessibility', () => {
  test('page has one h1 heading', async ({ page }) => {
    await page.goto('/');
    const h1s = await page.locator('h1').count();
    expect(h1s).toBe(1);
  });

  test('buttons have accessible names', async ({ page }) => {
    await page.goto('/modals');
    const buttons = await page.locator('button').all();
    
    for (const button of buttons) {
      const name = await button.getAttribute('aria-label') || 
                   await button.textContent() || 
                   'unnamed';
      expect(name).not.toBe('unnamed');
    }
  });

  test('modal traps focus', async ({ page }) => {
    await page.goto('/modals');
    await page.getByRole('button', { name: /Alert Dialog/i }).click();
    
    // Tab should stay within modal
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(['BUTTON', 'INPUT']).toContain(focusedElement);
  });
});
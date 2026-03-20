import { test, expect } from '@playwright/test';

test.describe('SSE Streaming', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('connection status shows green when connected', async ({ page }) => {
    const dot = page.locator('.rounded-full[title]').first();
    await expect(dot).toBeVisible({ timeout: 10000 });
    await expect(dot).toHaveAttribute('title', 'connected', { timeout: 10000 });
  });

  test('prices update in watchlist panel', async ({ page }) => {
    await page.waitForTimeout(3000);
    const prices = page.getByText(/\$\d+\.\d{2}/);
    await expect(prices.first()).toBeVisible({ timeout: 10000 });
    const count = await prices.count();
    expect(count).toBeGreaterThan(0);
  });

  test('sparklines appear after receiving price data', async ({ page }) => {
    await page.waitForTimeout(5000);
    // Sparklines are SVG elements in the watchlist
    const svgElements = page.locator('svg').first();
    await expect(svgElements).toBeVisible({ timeout: 15000 });
  });
});

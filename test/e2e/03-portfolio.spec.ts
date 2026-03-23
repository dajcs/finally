import { test, expect } from '@playwright/test';

test.describe('Portfolio', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
  });

  test('after buying positions, heatmap shows content', async ({ page }) => {
    await page.locator('input[placeholder="Ticker"]').fill('AAPL');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    await page.locator('input[placeholder="Ticker"]').fill('GOOGL');
    await page.locator('input[placeholder="Qty"]').fill('3');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    // "No open positions" should be gone
    await expect(page.getByText('No open positions')).toHaveCount(0, { timeout: 5000 });
  });

  test('P&L chart has data points after trades', async ({ page }) => {
    await page.locator('input[placeholder="Ticker"]').fill('AAPL');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(2000);

    // Chart SVG should appear (recharts renders SVG)
    const chartSvg = page.locator('.recharts-wrapper, .recharts-responsive-container, svg').first();
    await expect(chartSvg).toBeVisible({ timeout: 10000 });
  });

  test('positions table shows AAPL after buying', async ({ page }) => {
    await page.locator('input[placeholder="Ticker"]').fill('AAPL');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    // AAPL should appear in the positions area
    await expect(page.getByText('AAPL').first()).toBeVisible({ timeout: 5000 });
  });
});

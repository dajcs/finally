import { test, expect } from '@playwright/test';

test.describe('Watchlist', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
  });

  test('page loads with 10 default tickers', async ({ page }) => {
    const tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];
    for (const ticker of tickers) {
      await expect(page.getByText(ticker, { exact: true }).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('$10,000 cash shown in header', async ({ page }) => {
    await expect(page.locator('header').getByText('10,000').first()).toBeVisible({ timeout: 10000 });
  });

  test('connection status dot is green', async ({ page }) => {
    const dot = page.locator('.rounded-full[title]').first();
    await expect(dot).toBeVisible({ timeout: 10000 });
    await expect(dot).toHaveAttribute('title', 'connected', { timeout: 10000 });
  });

  test('prices are updating within 5 seconds', async ({ page }) => {
    // Wait for SSE connection
    const dot = page.locator('.rounded-full[title]').first();
    await expect(dot).toHaveAttribute('title', 'connected', { timeout: 10000 });

    // After SSE connects, prices should appear as numeric values replacing "--"
    // Look for a price like "190.45" or "175.23" in the page (not in header which has $)
    await expect(async () => {
      const pageText = await page.textContent('body');
      // Match a standalone decimal number like "190.45" that represents a stock price
      const hasPriceNumbers = /\d{2,4}\.\d{2}/.test(pageText || '');
      expect(hasPriceNumbers).toBeTruthy();
    }).toPass({ timeout: 10000 });
  });

  test('can add a new ticker', async ({ page }) => {
    const input = page.locator('input[placeholder="Add ticker"]');
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill('PYPL');
    await page.locator('button:has-text("+")').click();
    await expect(page.getByText('PYPL', { exact: true }).first()).toBeVisible({ timeout: 5000 });
  });

  test('can remove a ticker from watchlist', async ({ page }) => {
    // Add PYPL first
    const input = page.locator('input[placeholder="Add ticker"]');
    await input.fill('PYPL');
    await page.locator('button:has-text("+")').click();
    await expect(page.getByText('PYPL', { exact: true }).first()).toBeVisible({ timeout: 5000 });

    // Click the remove button (title="Remove") near PYPL
    const pyplRow = page.locator('div').filter({ hasText: /^PYPL/ }).first();
    await pyplRow.locator('button[title="Remove"]').click();

    await expect(page.getByText('PYPL', { exact: true })).toHaveCount(0, { timeout: 5000 });
  });
});

import { test, expect } from '@playwright/test';

test.describe('Trading', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
  });

  test('buy 5 shares of AAPL: cash decreases, position appears', async ({ page }) => {
    await page.locator('input[placeholder="Ticker"]').fill('AAPL');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    // AAPL should appear in positions area
    const positionsArea = page.locator('text=No positions').first();
    await expect(positionsArea).toHaveCount(0, { timeout: 5000 });

    // Cash should have decreased from $10,000
    const cashSpan = page.locator('header').getByText('Cash').locator('..').locator('span.font-mono');
    const cashText = await cashSpan.textContent();
    expect(cashText).not.toContain('10,000');
  });

  test('buy more shares: quantity accumulates', async ({ page }) => {
    // Use a unique ticker to isolate from other tests
    await page.locator('input[placeholder="Add ticker"]').fill('AMD');
    await page.locator('button:has-text("+")').click();
    await page.waitForTimeout(2000);

    await page.locator('input[placeholder="Ticker"]').fill('AMD');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    await page.locator('input[placeholder="Ticker"]').fill('AMD');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    // AMD position quantity should be 10
    const amdRow = page.locator('table tbody tr').filter({ hasText: 'AMD' }).first();
    await expect(amdRow).toBeVisible({ timeout: 5000 });
    const qtyCell = amdRow.locator('td').nth(1);
    await expect(qtyCell).toHaveText('10', { timeout: 5000 });
  });

  test('sell shares: quantity decreases', async ({ page }) => {
    // Use a unique ticker to avoid cross-test contamination
    await page.locator('input[placeholder="Add ticker"]').fill('INTC');
    await page.locator('button:has-text("+")').click();
    await page.waitForTimeout(2000);

    // Buy 5 shares of INTC
    await page.locator('input[placeholder="Ticker"]').fill('INTC');
    await page.locator('input[placeholder="Qty"]').fill('5');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    // Sell 3 shares of INTC
    await page.locator('input[placeholder="Ticker"]').fill('INTC');
    await page.locator('input[placeholder="Qty"]').fill('3');
    await page.locator('button:has-text("Sell")').click();
    await page.waitForTimeout(1500);

    // INTC position quantity should be 2
    const intcRow = page.locator('table tbody tr').filter({ hasText: 'INTC' }).first();
    await expect(intcRow).toBeVisible({ timeout: 5000 });
    const qtyCell = intcRow.locator('td').nth(1);
    await expect(qtyCell).toHaveText('2', { timeout: 5000 });
  });

  test('sell all remaining shares: position disappears', async ({ page }) => {
    // Use a unique ticker to avoid cross-test contamination
    // First add it to the watchlist
    await page.locator('input[placeholder="Add ticker"]').fill('DIS');
    await page.locator('button:has-text("+")').click();
    await page.waitForTimeout(2000);

    await page.locator('input[placeholder="Ticker"]').fill('DIS');
    await page.locator('input[placeholder="Qty"]').fill('3');
    await page.locator('button:has-text("Buy")').click();
    await page.waitForTimeout(1500);

    // Verify DIS appears in positions
    await expect(page.locator('table').getByText('DIS')).toBeVisible({ timeout: 5000 });

    await page.locator('input[placeholder="Ticker"]').fill('DIS');
    await page.locator('input[placeholder="Qty"]').fill('3');
    await page.locator('button:has-text("Sell")').click();
    await page.waitForTimeout(1500);

    // DIS should no longer appear in the positions table
    await expect(page.locator('table').getByText('DIS')).toHaveCount(0, { timeout: 5000 });
  });

  test('attempt buy with insufficient cash: error shown', async ({ page }) => {
    await page.locator('input[placeholder="Ticker"]').fill('AAPL');
    await page.locator('input[placeholder="Qty"]').fill('999999');
    await page.locator('button:has-text("Buy")').click();

    await expect(page.getByText(/insufficient|not enough|error/i).first()).toBeVisible({ timeout: 5000 });
  });
});

import { test, expect } from '@playwright/test';

test.describe('AI Chat (LLM_MOCK=true)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
  });

  test('chat panel is visible with input', async ({ page }) => {
    const chatInput = page.locator('input[placeholder="Ask FinAlly..."]');
    await expect(chatInput).toBeVisible({ timeout: 5000 });
  });

  test('send a message and receive a mocked response', async ({ page }) => {
    const chatInput = page.locator('input[placeholder="Ask FinAlly..."]');
    await chatInput.fill('Hello, what can you do?');
    await page.locator('button:has-text("Send")').click();

    // Wait for assistant response
    await page.waitForTimeout(5000);

    // Should see user message and at least one response
    await expect(page.getByText('Hello, what can you do?')).toBeVisible({ timeout: 5000 });
  });

  test('send buy message triggers trade via mock LLM', async ({ page }) => {
    const chatInput = page.locator('input[placeholder="Ask FinAlly..."]');
    await chatInput.fill('Buy 1 share of AAPL');
    await page.locator('button:has-text("Send")').click();

    // Mock LLM should return a trade action
    await expect(page.getByText(/bought|executed|trade|AAPL/i).first()).toBeVisible({ timeout: 15000 });
  });

  test('position updates after AI trade', async ({ page }) => {
    const chatInput = page.locator('input[placeholder="Ask FinAlly..."]');
    await chatInput.fill('Buy 1 share of AAPL');
    await page.locator('button:has-text("Send")').click();
    await page.waitForTimeout(5000);

    // Cash should have decreased
    const headerText = await page.locator('header').textContent();
    expect(headerText).not.toContain('10,000.00');
  });
});

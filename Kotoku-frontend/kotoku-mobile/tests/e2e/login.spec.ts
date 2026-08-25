import { test, expect } from '@playwright/test';

// The AuthGuard in app/_layout.tsx redirects unauthenticated sessions
// to /(auth)/welcome, so navigating to / is enough to reach the login flow.

test.describe('Login flow — smoke', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait past the "Starting…" splash (fonts + DB migrations load first)
    await expect(page.getByText("Don't take their word for it.")).toBeVisible({
      timeout: 20_000,
    });
  });

  test('welcome screen shows headline and CTA', async ({ page }) => {
    await expect(page.getByText("Don't take their word for it.")).toBeVisible();
    await expect(page.getByText('Take evidence for it.')).toBeVisible();
    await expect(page.getByText('Get started')).toBeVisible();
  });

  test('Get started navigates to phone entry', async ({ page }) => {
    await page.getByText('Get started').click();

    await expect(page.getByText('Enter your number')).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('🇬🇭 +233')).toBeVisible();
    await expect(page.getByText('Send code')).toBeVisible();
  });

  test('phone input accepts digits', async ({ page }) => {
    await page.getByText('Get started').click();

    const input = page.getByPlaceholder('XX XXX XXXX');
    await expect(input).toBeVisible({ timeout: 5_000 });
    await input.fill('241234567');
    await expect(input).toHaveValue('241234567');
  });
});

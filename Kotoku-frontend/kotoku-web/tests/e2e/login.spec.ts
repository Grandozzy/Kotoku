import { test, expect } from '@playwright/test';

// The session store (zustand + localStorage) gates rendering until hydrated.
// A fresh Playwright context has no localStorage, so hydration resolves
// instantly and the form renders without a redirect.

test.describe('Login flow — smoke', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    // Wait for the form to appear after Zustand hydration
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible({
      timeout: 10_000,
    });
  });

  test('login page renders phone form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await expect(page.getByText('🇬🇭 +233')).toBeVisible();
    await expect(page.getByPlaceholder('XX XXX XXXX')).toBeVisible();
    await expect(page.getByRole('button', { name: /send code/i })).toBeVisible();
  });

  test('Send code button is disabled until 9 digits are entered', async ({ page }) => {
    const button = page.getByRole('button', { name: /send code/i });
    await expect(button).toBeDisabled();

    await page.getByPlaceholder('XX XXX XXXX').fill('241234567');
    await expect(button).toBeEnabled();
  });

  test('submitting navigates to /verify with phone param', async ({ page }) => {
    // Intercept the OTP request so we don't need a live backend
    await page.route('**/api/auth/send-otp/', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{"message":"ok","expires_in_seconds":600}' })
    );

    await page.getByPlaceholder('XX XXX XXXX').fill('241234567');
    await page.getByRole('button', { name: /send code/i }).click();

    await expect(page).toHaveURL(/\/verify\?phone=%2B233241234567/, { timeout: 5_000 });
    await expect(page.getByRole('heading', { name: 'Enter your code' })).toBeVisible();
  });
});

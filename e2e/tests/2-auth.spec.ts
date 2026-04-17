/**
 * Auth flow tests — login page structure, form validation, redirect on success.
 * Full login/logout requires credentials (TEST_EMAIL / TEST_PASSWORD env vars).
 */

import { test, expect } from '@playwright/test'

test.describe('Login page structure', () => {
  test('renders email and password fields', async ({ page }) => {
    await page.goto('/auth/login')
    await expect(page.getByText('Sign in to your account')).toBeVisible()
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /Sign In/i })).toBeVisible()
  })

  test('shows link to sign-up page', async ({ page }) => {
    await page.goto('/auth/login')
    await expect(page.getByRole('link', { name: /Sign up/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Forgot password/i })).toBeVisible()
  })

  test('shows error on bad credentials', async ({ page }) => {
    await page.goto('/auth/login')
    await page.fill('input[type="email"]', 'nobody@example.invalid')
    await page.fill('input[type="password"]', 'wrongpassword123')
    await page.click('button[type="submit"]')
    // Should show an error message, not redirect
    await expect(page.locator('[class*="red"]')).toBeVisible({ timeout: 8_000 })
    await expect(page).not.toHaveURL('/')
  })
})

test.describe('Sign up page structure', () => {
  test('renders sign-up form', async ({ page }) => {
    await page.goto('/auth/signup')
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.getByRole('link', { name: /Sign in/i })).toBeVisible()
  })
})

test.describe('Login / logout (requires TEST_EMAIL + TEST_PASSWORD)', () => {
  test.skip(!process.env.TEST_EMAIL, 'TEST_EMAIL not set')

  test('logs in and lands on home page', async ({ page }) => {
    await page.goto('/auth/login')
    await page.fill('input[type="email"]', process.env.TEST_EMAIL!)
    await page.fill('input[type="password"]', process.env.TEST_PASSWORD!)
    await page.click('button[type="submit"]')
    await page.waitForURL('/', { timeout: 15_000 })
    await expect(page).toHaveURL('/')
    // Header should now show user name/email, not "Sign in"
    await expect(page.getByRole('link', { name: 'Sign in' })).not.toBeVisible()
  })

  test('sign-out button returns user to logged-out state', async ({ page }) => {
    // Log in first
    await page.goto('/auth/login')
    await page.fill('input[type="email"]', process.env.TEST_EMAIL!)
    await page.fill('input[type="password"]', process.env.TEST_PASSWORD!)
    await page.click('button[type="submit"]')
    await page.waitForURL('/')
    // Sign out
    await page.getByRole('button', { name: /Sign out/i }).click()
    // Should now see Sign in link again
    await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible({ timeout: 5_000 })
  })
})

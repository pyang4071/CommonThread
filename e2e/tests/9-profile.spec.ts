/**
 * Profile page — display name editor, content blocklist pickers, privacy toggle.
 */

import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/profile')
  await expect(page).toHaveURL('/profile')
})

test.describe('Profile page — layout', () => {
  test('shows Profile heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Profile/i }).first()).toBeVisible()
  })

  test('shows display name input', async ({ page }) => {
    await expect(
      page.locator('input[placeholder*="name" i], input[type="text"]').first()
    ).toBeVisible()
  })

  test('shows privacy toggle', async ({ page }) => {
    // Profile public toggle — rendered as a checkbox or toggle button
    await expect(
      page.locator('input[type="checkbox"], [role="switch"]').first()
    ).toBeVisible()
  })

  test('shows content blocklist section', async ({ page }) => {
    // Should mention blocked genres/types/tones somewhere
    await expect(
      page.getByText(/Block|blocklist|genre/i).first()
    ).toBeVisible()
  })
})

test.describe('Profile page — name edit', () => {
  test('name input accepts text', async ({ page }) => {
    const input = page.locator('input[type="text"]').first()
    await input.fill('Test Display Name')
    const value = await input.inputValue()
    expect(value).toBe('Test Display Name')
  })
})

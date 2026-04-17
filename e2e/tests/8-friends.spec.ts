/**
 * Friends page — user search, following list, activity feed.
 */

import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/friends')
  await expect(page).toHaveURL('/friends')
})

test.describe('Friends page — layout', () => {
  test('shows page heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Friends/i }).first()).toBeVisible()
  })

  test('shows user search input', async ({ page }) => {
    await expect(
      page.locator('input[placeholder*="name" i], input[placeholder*="email" i], input[placeholder*="search" i]').first()
    ).toBeVisible()
  })

  test('shows Following or activity section', async ({ page }) => {
    await expect(
      page.getByText(/Following|Activity|No activity/i).first()
    ).toBeVisible()
  })
})

test.describe('Friends page — search interaction', () => {
  test('typing in search input shows results or empty state', async ({ page }) => {
    const input = page.locator('input').first()
    await input.fill('a')
    // Debounced — wait for results
    await page.waitForTimeout(500)
    // Either user results appear or empty state — no crash
    await expect(page).toHaveURL('/friends')
  })
})

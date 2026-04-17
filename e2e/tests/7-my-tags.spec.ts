/**
 * My Tags page — explanation callout, search filter, tag cards.
 */

import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/my-tags')
  await expect(page).toHaveURL('/my-tags')
})

test.describe('My Tags page — layout', () => {
  test('shows page heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /My Tags|Tags/i }).first()).toBeVisible()
  })

  test('shows explanation callout banner', async ({ page }) => {
    // The callout explains how personal tags influence recommendations
    await expect(page.locator('[class*="indigo-50"], [class*="callout"], [class*="bg-indigo"]').first()).toBeVisible()
  })

  test('shows filter/search input', async ({ page }) => {
    await expect(
      page.locator('input[placeholder*="filter" i], input[placeholder*="search" i]').first()
    ).toBeVisible()
  })
})

test.describe('My Tags page — filter', () => {
  test('filter input runs without error', async ({ page }) => {
    const input = page.locator('input[placeholder*="filter" i], input[placeholder*="search" i]').first()
    await input.fill('test')
    await page.waitForTimeout(200)
    // No crash — URL stays the same
    await expect(page).toHaveURL('/my-tags')
  })
})

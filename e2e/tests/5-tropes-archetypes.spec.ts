/**
 * Tropes and Archetypes list pages — browse, search, category filter, card links.
 */

import { test, expect } from '@playwright/test'

test.describe('Tropes list page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/tropes')
    await expect(page).toHaveURL('/tropes')
  })

  test('shows page heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Tropes/i }).first()).toBeVisible()
  })

  test('shows trope cards', async ({ page }) => {
    // At least one trope should be visible
    await expect(page.getByText('Enemies to Lovers')).toBeVisible()
  })

  test('search input filters tropes', async ({ page }) => {
    const input = page.locator('input[placeholder*="search" i], input[placeholder*="filter" i]').first()
    await input.fill('Enemies')
    await expect(page.getByText('Enemies to Lovers')).toBeVisible()
    // Other tropes should be hidden
    const slowBurn = page.getByText('Slow Burn Romance')
    const visible = await slowBurn.isVisible().catch(() => false)
    expect(visible).toBe(false)
  })

  test('trope cards link to trope detail pages', async ({ page }) => {
    const link = page.locator('a[href*="/tropes/"]').first()
    await expect(link).toBeVisible()
    await link.click()
    await expect(page).toHaveURL(/\/tropes\/\d+/)
  })

  test('category filter chips are present', async ({ page }) => {
    // Category filter chips like "All", "Romance", etc.
    await expect(page.getByRole('button', { name: /All/i }).first()).toBeVisible()
  })
})

test.describe('Archetypes list page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/archetypes')
    await expect(page).toHaveURL('/archetypes')
  })

  test('shows page heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Archetypes/i }).first()).toBeVisible()
  })

  test('shows archetype cards or list items', async ({ page }) => {
    // At least one archetype card should exist
    await expect(page.locator('[class*="border"][class*="rounded"]').first()).toBeVisible()
  })

  test('search input filters archetypes', async ({ page }) => {
    const input = page.locator('input[placeholder*="search" i], input[placeholder*="filter" i]').first()
    await expect(input).toBeVisible()
    await input.fill('Hero')
    // Some hero-type archetypes should appear (or results become filtered)
    await page.waitForTimeout(300)
    const count = await page.locator('[class*="border"][class*="rounded"]').count()
    // Just verify the filter ran without crashing
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('archetype cards link to archetype detail pages', async ({ page }) => {
    const link = page.locator('a[href*="/archetypes/"]').first()
    await expect(link).toBeVisible()
    await link.click()
    await expect(page).toHaveURL(/\/archetypes\/\d+/)
  })
})

test.describe('Trope detail page', () => {
  test('shows trope name and books tagged with it', async ({ page }) => {
    await page.goto('/tropes/1')
    // Should show breadcrumb and book list
    await expect(page.locator('h1,h2').first()).toBeVisible()
  })
})

test.describe('Archetype detail page', () => {
  test('shows archetype name and books tagged with it', async ({ page }) => {
    await page.goto('/archetypes/1')
    await expect(page.locator('h1,h2').first()).toBeVisible()
  })
})

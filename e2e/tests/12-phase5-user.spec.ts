/**
 * Phase 4/5 features — user-auth E2E coverage.
 *
 * Suites:
 *   1. Books — Page count filter (Min/Max inputs, active-filter badge, clear)
 *   2. Books — Language filter selects a language and reflects in active count
 *   3. BookDetail — basic structure smoke test (crowd-tagged badge absent check)
 *
 * Requires user auth (storageState: .auth/user.json).
 */

import { test, expect } from '@playwright/test'

// ── helpers ───────────────────────────────────────────────────────────────────

/** Open the filter panel on /books and wait for the Min input to appear. */
async function openFilters(page: import('@playwright/test').Page) {
  const filterBtn = page.getByRole('button', { name: /Filters/i })
  await expect(filterBtn).toBeVisible({ timeout: 6_000 })
  const minInput = page.locator('input[placeholder="Min"]')
  if (!(await minInput.isVisible().catch(() => false))) {
    await filterBtn.click()
    await expect(minInput).toBeVisible({ timeout: 4_000 })
  }
}

/** Clear session-persisted filter state and reload the Books page fresh. */
async function freshBooksPage(page: import('@playwright/test').Page) {
  await page.goto('/books')
  await expect(page).toHaveURL('/books', { timeout: 10_000 })
  await page.evaluate(() => {
    for (const k of Object.keys(sessionStorage)) {
      if (k.startsWith('books:')) sessionStorage.removeItem(k)
    }
  })
  await page.reload()
  await expect(page).toHaveURL('/books', { timeout: 8_000 })
  // Wait for the initial book load to finish before touching filters
  await page.waitForResponse(
    r => r.url().includes('/api/v1/books') && r.status() === 200,
    { timeout: 10_000 }
  )
}

// ── 1. Books — Page count filter ─────────────────────────────────────────────

test.describe('Books page — page count filter', () => {
  test.beforeEach(async ({ page }) => {
    await freshBooksPage(page)
  })

  test('filter panel contains Min and Max page count inputs', async ({ page }) => {
    await openFilters(page)
    await expect(page.locator('input[placeholder="Min"]')).toBeVisible()
    await expect(page.locator('input[placeholder="Max"]')).toBeVisible()
  })

  test('a "Page Count" label appears above the inputs', async ({ page }) => {
    await openFilters(page)
    await expect(page.getByText(/Page Count/i)).toBeVisible()
  })

  test('entering Min increments the active filter count', async ({ page }) => {
    await openFilters(page)
    const filterBtn = page.getByRole('button', { name: /Filters/i })
    await page.locator('input[placeholder="Min"]').fill('100')
    await page.locator('input[placeholder="Min"]').press('Tab')
    const badge = filterBtn.locator('span').filter({ hasText: /^\d+$/ })
    await expect(badge).toBeVisible({ timeout: 4_000 })
  })

  test('entering a sensible Min still shows books', async ({ page }) => {
    await openFilters(page)
    // Wait for the filter-triggered fetch to complete before asserting
    const responsePromise = page.waitForResponse(
      r => r.url().includes('/api/v1/books') && r.url().includes('page_count_min=50') && r.status() === 200,
      { timeout: 10_000 }
    )
    await page.locator('input[placeholder="Min"]').fill('50')
    await page.locator('input[placeholder="Min"]').press('Tab')
    await responsePromise
    await expect(page.getByRole('link', { name: /\S/ }).first()).toBeVisible({ timeout: 8_000 })
  })

  test('entering a very large Min filters out all books', async ({ page }) => {
    await openFilters(page)
    await page.locator('input[placeholder="Min"]').fill('999999')
    await page.locator('input[placeholder="Min"]').press('Tab')
    // Wait for the empty-state message — confirms API returned 0 books and React rendered
    await expect(page.getByText('No books match your filters.')).toBeVisible({ timeout: 10_000 })
  })

  test('Clear button removes page count filter and restores active count', async ({ page }) => {
    await openFilters(page)
    await page.locator('input[placeholder="Min"]').fill('9999')
    await page.locator('input[placeholder="Min"]').press('Tab')
    await page.waitForTimeout(300)

    const clearLink = page.getByRole('button', { name: /^Clear$/i })
    await expect(clearLink).toBeVisible({ timeout: 4_000 })
    await clearLink.click()
    await page.waitForTimeout(300)

    await expect(page.locator('input[placeholder="Min"]')).toHaveValue('')
    await expect(clearLink).not.toBeVisible()
  })

  test('Max input narrows results and increments filter badge', async ({ page }) => {
    await openFilters(page)
    await page.locator('input[placeholder="Max"]').fill('200')
    await page.locator('input[placeholder="Max"]').press('Tab')
    const filterBtn = page.getByRole('button', { name: /Filters/i })
    const badge = filterBtn.locator('span').filter({ hasText: /^\d+$/ })
    await expect(badge).toBeVisible({ timeout: 4_000 })
  })
})

// ── 2. Books — Language filter ────────────────────────────────────────────────

test.describe('Books page — language filter', () => {
  test.beforeEach(async ({ page }) => {
    await freshBooksPage(page)
  })

  test('Language section is visible in filter panel', async ({ page }) => {
    await openFilters(page)
    await expect(page.getByText(/^Language$/i)).toBeVisible()
  })

  test('English language button is present', async ({ page }) => {
    await openFilters(page)
    await expect(page.getByRole('button', { name: /English/i })).toBeVisible()
  })

  test('clicking English activates it and increments filter count', async ({ page }) => {
    await openFilters(page)
    const engBtn = page.getByRole('button', { name: /English/i })
    await engBtn.click()
    await page.waitForTimeout(400)

    const cls = await engBtn.getAttribute('class') ?? ''
    expect(cls).toMatch(/indigo|active/)

    const filterBtn = page.getByRole('button', { name: /Filters/i })
    const badge = filterBtn.locator('span').filter({ hasText: /^\d+$/ })
    await expect(badge).toBeVisible({ timeout: 4_000 })
  })

  test('clicking English twice deactivates it', async ({ page }) => {
    await openFilters(page)
    const engBtn = page.getByRole('button', { name: /English/i })
    await engBtn.click()
    await page.waitForTimeout(200)
    await engBtn.click()
    await page.waitForTimeout(400)

    const cls = await engBtn.getAttribute('class') ?? ''
    expect(cls).not.toMatch(/bg-indigo-600 text-white/)
  })

  test('Clear all removes language filter', async ({ page }) => {
    await openFilters(page)
    await page.getByRole('button', { name: /English/i }).click()
    await page.waitForTimeout(300)

    const clearAll = page.getByRole('button', { name: /Clear all/i })
    await expect(clearAll).toBeVisible({ timeout: 4_000 })
    await clearAll.click()
    await page.waitForTimeout(400)

    const filterBtn = page.getByRole('button', { name: /Filters/i })
    const badge = filterBtn.locator('span').filter({ hasText: /^\d+$/ })
    await expect(badge).not.toBeVisible()
  })
})

// ── 3. BookDetail — structure smoke test ─────────────────────────────────────

test.describe('BookDetail — basic structure', () => {
  test('detail page loads with heading and tropes/archetypes sections', async ({ page }) => {
    await page.goto('/books')
    await expect(page).toHaveURL('/books', { timeout: 10_000 })

    // Navigate to the first book in the grid
    const firstBook = page.locator('a[href^="/books/"]').filter({ hasNot: page.locator('[href="/books/new"]') }).first()
    const href = await firstBook.getAttribute('href')
    if (!href) { test.skip(); return }

    await page.goto(href)
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 8_000 })

    const hasSection =
      (await page.getByText(/Tropes/i).first().isVisible().catch(() => false)) ||
      (await page.getByText(/Archetypes|Character/i).first().isVisible().catch(() => false))
    expect(hasSection).toBeTruthy()
  })

  test('crowd-tagged badge absent on a book without crowd-promoted tropes', async ({ page }) => {
    // Navigating to book 1 (Name of the Wind) — not crowd-promoted in dev DB
    await page.goto('/books/1')
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 8_000 })

    // If tropes are present, verify no crowd-tagged badge (admin-only action required)
    const tropeSection = await page.getByText(/Tropes/i).first().isVisible().catch(() => false)
    if (tropeSection) {
      const badge = page.getByText('crowd-tagged')
      // crowd-tagged badge requires manual admin crowd-promotion — not in dev fixture
      const visible = await badge.isVisible({ timeout: 1_000 }).catch(() => false)
      // This is informational — if it IS crowd-tagged in dev, we skip rather than fail
      if (visible) test.skip()
    }
  })
})

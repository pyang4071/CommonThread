/**
 * Shelf page — three status sections, sort controls, title/author filter.
 */

import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/shelf')
  await expect(page).toHaveURL('/shelf')
})

test.describe('Shelf page — layout', () => {
  test('shows page heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /My Shelf|Shelf/i }).first()).toBeVisible()
  })

  test('renders three status sections headings', async ({ page }) => {
    // Even if empty, the section headings should be present
    await expect(page.getByText(/Currently Reading/i)).toBeVisible()
    await expect(page.getByText(/Want to Read/i)).toBeVisible()
    await expect(page.getByText(/Read/i).first()).toBeVisible()
  })

  test('sort select is visible when shelf is non-empty', async ({ page }) => {
    // If user has books, a sort dropdown should be present
    const hasBooks = await page.locator('[class*="border"][class*="rounded"]').count() > 0
    if (hasBooks) {
      await expect(page.locator('select')).toBeVisible()
    }
  })

  test('filter input is present', async ({ page }) => {
    await expect(
      page.locator('input[placeholder*="filter" i], input[placeholder*="title" i]').first()
    ).toBeVisible()
  })
})

test.describe('Shelf page — sort and filter', () => {
  test('sort control changes order label', async ({ page }) => {
    const hasBooks = await page.locator('select').count() > 0
    if (!hasBooks) {
      test.skip()
      return
    }
    const select = page.locator('select').first()
    await select.selectOption({ label: /Title A.Z/i })
    // No crash and URL unchanged (client-side sort)
    await expect(page).toHaveURL('/shelf')
  })

  test('filter input hides non-matching books', async ({ page }) => {
    const books = await page.locator('a[href*="/books/"]').count()
    if (books === 0) {
      test.skip()
      return
    }
    const filter = page.locator('input[placeholder*="filter" i], input[placeholder*="title" i]').first()
    await filter.fill('zzzzznonexistent')
    // All sections should show no results or be hidden
    await page.waitForTimeout(200)
    const remaining = await page.locator('a[href*="/books/"]').count()
    expect(remaining).toBeLessThan(books)
  })
})

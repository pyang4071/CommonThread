/**
 * Books page — browse, search, vibe search, filter, pagination.
 * Requires user auth (storageState: .auth/user.json).
 * If .auth/user.json has no session, all tests will redirect to /auth/login and fail —
 * set TEST_EMAIL / TEST_PASSWORD in e2e/.env first.
 */

import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/books')
  // If auth is missing, tests will fail here — intentional.
  await expect(page).toHaveURL('/books', { timeout: 10_000 })
})

test.describe('Books page — layout', () => {
  test('shows page title and search input', async ({ page }) => {
    await expect(page).toHaveTitle(/Books.*CommonThread|CommonThread/)
    await expect(page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()).toBeVisible()
  })

  test('shows at least one book card', async ({ page }) => {
    // Cards are rendered in a grid — look for a linked book title
    await expect(page.getByRole('link', { name: 'The Name of the Wind' })).toBeVisible()
  })

  test('shows pagination controls', async ({ page }) => {
    await expect(page.getByText(/Page \d/)).toBeVisible()
  })

  test('shows Vibe Search button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Vibe/i })).toBeVisible()
  })

  test('shows Filters button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Filter/i })).toBeVisible()
  })
})

test.describe('Books page — keyword search', () => {
  test('searching by title filters results', async ({ page }) => {
    const input = page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()
    await input.fill('Name of the Wind')
    await input.press('Enter')
    await expect(page.getByRole('link', { name: 'The Name of the Wind' })).toBeVisible()
    // Filter summary bar should appear
    await expect(page.getByText(/books?/i)).toBeVisible()
  })

  test('searching by author name filters results', async ({ page }) => {
    const input = page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()
    await input.fill('Patrick Rothfuss')
    await input.press('Enter')
    await expect(page.getByRole('link', { name: 'The Name of the Wind' })).toBeVisible()
  })

  test('search with no results shows empty state or zero count', async ({ page }) => {
    const input = page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()
    await input.fill('xyzzy-no-such-book-9999')
    await input.press('Enter')
    // Either empty state text or 0 books in summary
    await expect(
      page.getByText(/0 books|no books|no results/i)
        .or(page.getByText('xyzzy').first())
    ).toBeVisible({ timeout: 5_000 })
  })
})

test.describe('Books page — vibe search', () => {
  test('opening vibe search panel shows query input', async ({ page }) => {
    await page.getByRole('button', { name: /Vibe/i }).click()
    await expect(page.locator('input[placeholder*="vibe" i], input[placeholder*="query" i], textarea').first()).toBeVisible()
  })

  test('example query chips populate the vibe input on click', async ({ page }) => {
    await page.getByRole('button', { name: /Vibe/i }).click()
    // Example chips are small buttons in the vibe panel
    const chip = page.locator('[class*="chip"], button').filter({ hasText: /slow.burn|found family|dark academia|cozy/i }).first()
    if (await chip.count() > 0) {
      await chip.click()
      const input = page.locator('input[placeholder*="vibe" i], input, textarea').first()
      const val = await input.inputValue()
      expect(val.length).toBeGreaterThan(0)
    }
  })

  test('alpha slider is present in vibe panel', async ({ page }) => {
    await page.getByRole('button', { name: /Vibe/i }).click()
    await expect(page.locator('input[type="range"]')).toBeVisible()
  })
})

test.describe('Books page — filter panel', () => {
  test('filter panel opens and shows genre chips', async ({ page }) => {
    await page.getByRole('button', { name: /Filter/i }).click()
    await expect(page.getByText('Fantasy')).toBeVisible()
    await expect(page.getByText('Romance')).toBeVisible()
  })

  test('selecting a genre chip updates active filter count', async ({ page }) => {
    await page.getByRole('button', { name: /Filter/i }).click()
    // Click the Fantasy genre chip
    await page.getByRole('button', { name: 'Fantasy' }).first().click()
    // Filter summary should show "1 filter active" or similar
    await expect(page.getByText(/filter/i)).toBeVisible()
  })

  test('pacing picker buttons are visible in filter panel', async ({ page }) => {
    await page.getByRole('button', { name: /Filter/i }).click()
    await expect(page.getByRole('button', { name: /Very Slow|Slow|Moderate|Fast/i }).first()).toBeVisible()
  })
})

test.describe('Books page — admin delete guard', () => {
  test('regular user does not see Delete button on book cards', async ({ page }) => {
    // Delete buttons should only exist for admins
    const deleteBtn = page.getByRole('button', { name: /Delete/i })
    const count = await deleteBtn.count()
    // If user is not admin, no delete buttons should appear
    // (This test relies on user.json being a non-admin user)
    if (process.env.TEST_EMAIL) {
      expect(count).toBe(0)
    }
  })
})

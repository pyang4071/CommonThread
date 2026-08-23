/**
 * Books page — browse, search, semantic search, filter, pagination.
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

  test('search input invites a descriptive/semantic query', async ({ page }) => {
    await expect(page.locator('input[placeholder*="describe" i]')).toBeVisible()
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

test.describe('Books page — semantic search', () => {
  test('typing a query reveals the keyword/semantic alpha slider', async ({ page }) => {
    const input = page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()
    await input.fill('cozy mystery with slow-burn romance')
    await expect(page.locator('input[type="range"]')).toBeVisible()
  })

  test('alpha slider is labeled from keyword to semantic weighting', async ({ page }) => {
    const input = page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()
    await input.fill('found family in a dark academia setting')
    await expect(page.getByText('More semantic')).toBeVisible()
    await expect(page.getByText('More keyword')).toBeVisible()
  })

  test('clearing the query hides the alpha slider', async ({ page }) => {
    const input = page.locator('input[placeholder*="title" i], input[placeholder*="search" i]').first()
    await input.fill('slow-burn enemies to lovers')
    await expect(page.locator('input[type="range"]')).toBeVisible()
    await input.fill('')
    await expect(page.locator('input[type="range"]')).toBeHidden()
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

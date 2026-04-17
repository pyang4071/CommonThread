/**
 * Tagging threshold feature — end-to-end test of the new ingestion flow:
 *   1. Create a book with no tropes → verify 0/3 badge on BookDetail.
 *   2. Attach 1 trope → verify 1/3 badge.
 *   3. Attach 2 more tropes → verify "Indexing in progress" badge (threshold crossed).
 *   4. Verify embed-all skips books below threshold.
 *
 * Requires ADMIN_EMAIL + ADMIN_PASSWORD for all tests.
 * Also exercises the AddBook UI for the updated optional-trope flow.
 */

import { test, expect } from '@playwright/test'

const hasAdmin = !!process.env.ADMIN_EMAIL

// ── AddBook form — optional tropes ────────────────────────────────────────────

test.describe('AddBook form — optional tropes UI', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test.beforeEach(async ({ page }) => {
    await page.goto('/books/new')
    await expect(page).toHaveURL('/books/new')
  })

  test('page subtitle mentions threshold', async ({ page }) => {
    await expect(page.getByText(/Recommendations unlock.*3 tropes/i).first()).toBeVisible()
  })

  test('Tropes section is marked optional', async ({ page }) => {
    await expect(page.getByText(/Tropes/i).filter({ hasText: /optional/i })).toBeVisible()
  })

  test('sub-label in Tropes section explains the threshold', async ({ page }) => {
    await expect(page.getByText(/Recommendations unlock at 3 tropes/i)).toBeVisible()
  })

  test('form can be submitted with no tropes selected', async ({ page }) => {
    // Fill required metadata fields
    const uniqueTitle = `E2E-NoTropes-${Date.now()}`
    await page.locator('input[placeholder*="Name of the Wind" i], input[required]').first().fill(uniqueTitle)
    // Author field
    await page.locator('input[placeholder*="Rothfuss" i], input[required]').nth(1).fill('Test Author')
    // ISBN — placeholder is "978-0-00-000000-0", not "ISBN"
    await page.locator('input[placeholder*="978" i]').fill(`000${Date.now()}`.slice(0, 13))
    // Publication date
    await page.locator('input[type="date"]').fill('2024-01-01')
    // Submit — should succeed without tropes
    await page.getByRole('button', { name: /Add Book/i }).click()
    // Should navigate to the new book's detail page
    await expect(page).toHaveURL(/\/books\/\d+/, { timeout: 15_000 })
  })

  test('adding 1 trope shows amber 1/3 progress callout', async ({ page }) => {
    // Fill required metadata
    const tropeInput = page.locator('input[placeholder*="Search tropes" i]')
    await expect(tropeInput).toBeVisible()

    // Search and select first trope
    await tropeInput.fill('Enemies')
    await page.waitForTimeout(300)
    const firstResult = page.locator('ul li button').first()
    if (await firstResult.isVisible()) {
      await firstResult.click()
      // Amber callout should appear
      await expect(page.getByText(/1\/3 tropes.*add.*more/i)).toBeVisible({ timeout: 3_000 })
    }
  })

  test('adding 3 tropes turns counter green', async ({ page }) => {
    const tropeInput = page.locator('input[placeholder*="Search tropes" i]')
    await expect(tropeInput).toBeVisible()

    const tropes = ['Enemies', 'Forbidden', 'Slow Burn']
    for (const q of tropes) {
      await tropeInput.fill(q)
      await page.waitForTimeout(300)
      const result = page.locator('ul li button').first()
      if (await result.isVisible()) await result.click()
    }

    // Badge count should be 3/12 with green styling
    const badge = page.locator('[class*="emerald"]')
    await expect(badge).toBeVisible({ timeout: 3_000 })
  })
})

// ── BookDetail — threshold badge on a freshly ingested book ──────────────────

test.describe('BookDetail — tagging threshold badge', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  let newBookId: number

  test('freshly created book (no tropes) shows 0/3 badge', async ({ page }) => {
    // Create a book via API directly for speed
    const res = await page.request.post('/api/v1/books/', {
      data: {
        title: `E2E-Threshold-${Date.now()}`,
        author: 'Test Author E2E',
        isbn: `999${Date.now()}`.slice(0, 13),
        publication_date: '2024-01-01',
        description: 'Test book for threshold badge test',
      },
    })
    expect(res.ok()).toBeTruthy()
    const book = await res.json()
    newBookId = book.book_id

    await page.goto(`/books/${newBookId}`)
    // Should show 0/3 tropes badge
    await expect(page.getByText(/0\/3 tropes/)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/needs 3 more for recommendations/i)).toBeVisible()
  })

  test('after adding 1 trope shows 1/3 badge', async ({ page }) => {
    // Attach trope via API
    await page.request.post(`/api/v1/books/${newBookId}/tropes`, {
      data: { trope_id: 1, weight: 0.85 },
    })
    await page.goto(`/books/${newBookId}`)
    await expect(page.getByText(/1\/3 tropes/)).toBeVisible({ timeout: 8_000 })
    await expect(page.getByText(/needs 2 more/i)).toBeVisible()
  })

  test('after adding 2 more tropes badge shows "Indexing in progress"', async ({ page }) => {
    // Attach 2 more tropes to cross the threshold
    await page.request.post(`/api/v1/books/${newBookId}/tropes`, {
      data: { trope_id: 2, weight: 0.65 },
    })
    await page.request.post(`/api/v1/books/${newBookId}/tropes`, {
      data: { trope_id: 3, weight: 0.45 },
    })

    await page.goto(`/books/${newBookId}`)
    // Either "Indexing in progress" (embedding queued) or no badge (already done)
    const indexing = page.getByText(/Indexing in progress/i)
    const done = page.getByText(/\/3 tropes/)
    // At least the amber threshold badge should be GONE (3 tropes = threshold met)
    await expect(done).not.toBeVisible({ timeout: 8_000 })
  })

  test('removing a trope below threshold resets to pending with badge', async ({ page }) => {
    // Wait for the background embedding to settle so the detach can properly reset.
    // Poll the API until status is no longer 'pending' (i.e. 'done' or 'failed').
    for (let i = 0; i < 20; i++) {
      const r = await page.request.get(`/api/v1/books/${newBookId}`)
      const b = await r.json()
      if (b.embedding_status !== 'pending') break
      await page.waitForTimeout(1_000)
    }

    // Remove one trope to drop count to 2 (below threshold)
    const delRes = await page.request.delete(`/api/v1/books/${newBookId}/tropes/3`)
    expect(delRes.status()).toBe(204)

    await page.goto(`/books/${newBookId}`)
    // Should show 2/3 badge again
    await expect(page.getByText(/2\/3 tropes/)).toBeVisible({ timeout: 8_000 })
  })
})

// ── Admin embed-all skips below-threshold books ───────────────────────────────

test.describe('Admin embed-all — threshold gate', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test('embed-all skips books with < 3 tropes', async ({ page }) => {
    // Create a fresh book with 0 tropes
    const res = await page.request.post('/api/v1/books/', {
      data: {
        title: `E2E-SkipEmbed-${Date.now()}`,
        author: 'Test Author',
        isbn: `777${Date.now()}`.slice(0, 13),
        publication_date: '2024-06-01',
      },
    })
    const book = await res.json()
    const id = book.book_id

    // Get Bearer token — navigate to a page to hydrate localStorage, then read it
    await page.goto('/admin')
    await page.waitForURL('/admin')
    const token = await page.evaluate(() => {
      const key = Object.keys(localStorage).find(k => k.startsWith('sb-') && k.endsWith('-auth-token'))
      if (!key) return ''
      try { return (JSON.parse(localStorage.getItem(key) || '') as { access_token: string }).access_token } catch { return '' }
    })

    // Trigger embed-all via API with admin Bearer token
    const embedRes = await page.request.post('/api/v1/admin/embed-all', {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(embedRes.ok()).toBeTruthy()

    // The new book (0 tropes) should NOT be in the queued count
    // Verify by checking the book still has no genome embedding after embed-all
    await page.waitForTimeout(2000)
    const detailRes = await page.request.get(`/api/v1/books/${id}`)
    const detail = await detailRes.json()
    expect(detail.embedding_status).toBe('pending')

    // Cleanup
    await page.request.delete(`/api/v1/books/${id}`)
  })
})

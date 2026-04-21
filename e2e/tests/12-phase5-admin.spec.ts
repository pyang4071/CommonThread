/**
 * Phase 4/5 features — admin-auth E2E coverage.
 *
 * Suites:
 *   1. Admin — Vector Coverage panel shows "Review-embedded" stat
 *   2. Admin — Embedding Models health panel with three named model pills
 *   3. Tropes — Delete shows ConfirmModal; cancelling leaves trope intact
 *   4. Archetypes — Delete shows ConfirmModal; cancelling leaves archetype intact
 *   5. BookDetail — crowd-tagged badge absent before promotion threshold
 *
 * Requires admin auth (storageState: .auth/admin.json).
 * All tests skip when ADMIN_EMAIL is not set.
 */

import { test, expect } from '@playwright/test'

const hasAdmin = !!process.env.ADMIN_EMAIL

// ── 1. Admin — Vector Coverage: review-embedded stat ─────────────────────────

test.describe('Admin — Vector Coverage review-embedded stat', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test.beforeEach(async ({ page }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL('/admin', { timeout: 10_000 })
  })

  test('Vector Coverage heading is visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Vector Coverage/i })).toBeVisible({ timeout: 8_000 })
  })

  test('Review-embedded stat card is visible', async ({ page }) => {
    await expect(page.getByText(/Review-embedded/i)).toBeVisible({ timeout: 10_000 })
  })

  test('review-embedded stat card contains a numeric count', async ({ page }) => {
    await expect(page.getByText(/Review-embedded/i)).toBeVisible({ timeout: 10_000 })
    // The outer card is the col-span-2 div; scope to the first sky-class div (the card container)
    const card = page.locator('div[class*="sky-50"]').filter({ hasText: /Review-embedded/i }).first()
    await expect(card).toBeVisible({ timeout: 6_000 })
    const text = await card.innerText()
    expect(/\d/.test(text)).toBeTruthy()
  })

  test('clicking Refresh reloads coverage data without error', async ({ page }) => {
    // Vector Coverage panel has its own Refresh button (first one on page)
    const refreshBtns = page.getByRole('button', { name: /^Refresh$/i })
    await expect(refreshBtns.first()).toBeVisible({ timeout: 8_000 })
    await refreshBtns.first().click()
    await expect(page.getByText(/Review-embedded/i)).toBeVisible({ timeout: 8_000 })
  })
})

// ── 2. Admin — Embedding Models health panel ──────────────────────────────────

test.describe('Admin — Embedding Models health panel', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test.beforeEach(async ({ page }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL('/admin', { timeout: 10_000 })
  })

  test('Embedding Models heading is visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Embedding Models/i })).toBeVisible({ timeout: 8_000 })
  })

  test('shows genome model pill', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /Embedding Models/i })
    await expect(heading).toBeVisible({ timeout: 8_000 })
    const panel = heading.locator('xpath=ancestor::div[contains(@class,"rounded-xl")]')
    await expect(panel.getByText(/genome/i)).toBeVisible({ timeout: 6_000 })
  })

  test('shows description model pill', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /Embedding Models/i })
    await expect(heading).toBeVisible({ timeout: 8_000 })
    const panel = heading.locator('xpath=ancestor::div[contains(@class,"rounded-xl")]')
    await expect(panel.getByText(/description/i)).toBeVisible({ timeout: 6_000 })
  })

  test('shows review model pill', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /Embedding Models/i })
    await expect(heading).toBeVisible({ timeout: 8_000 })
    const panel = heading.locator('xpath=ancestor::div[contains(@class,"rounded-xl")]')
    await expect(panel.getByText(/review/i)).toBeVisible({ timeout: 6_000 })
  })

  test('model pills show Ready or Loading status', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Embedding Models/i })).toBeVisible({ timeout: 8_000 })
    await expect(page.getByText(/Ready|Loading/i).first()).toBeVisible({ timeout: 6_000 })
  })

  test('three model pills are rendered', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /Embedding Models/i })
    await expect(heading).toBeVisible({ timeout: 10_000 })
    const panel = heading.locator('xpath=ancestor::div[contains(@class,"rounded-xl")]')
    // Pills are small divs with a model name <p> and a status <p>
    const namePills = panel.locator('p.text-xs.font-medium')
    await expect(namePills).toHaveCount(3, { timeout: 6_000 })
  })
})

// ── 3. Tropes — ConfirmModal on delete ────────────────────────────────────────

test.describe('Tropes page — delete confirm modal', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test.beforeEach(async ({ page }) => {
    await page.goto('/tropes')
    await expect(page).toHaveURL('/tropes', { timeout: 10_000 })
  })

  test('Delete button exists on at least one trope card', async ({ page }) => {
    await expect(page.getByRole('button', { name: /^Delete$/i }).first()).toBeVisible({ timeout: 8_000 })
  })

  test('clicking Delete opens a confirmation modal', async ({ page }) => {
    await page.getByRole('button', { name: /^Delete$/i }).first().click()
    // ConfirmModal renders a dialog overlay
    await expect(
      page.getByRole('dialog').or(page.locator('[class*="fixed"][class*="inset"]'))
    ).toBeVisible({ timeout: 4_000 })
  })

  test('modal shows Cancel and Delete confirm buttons', async ({ page }) => {
    await page.getByRole('button', { name: /^Delete$/i }).first().click()
    await expect(page.getByRole('button', { name: /Cancel/i })).toBeVisible({ timeout: 4_000 })
    // The last Delete/Confirm button is inside the modal
    await expect(page.getByRole('button', { name: /Delete|Confirm/i }).last()).toBeVisible({ timeout: 4_000 })
  })

  test('cancelling the modal leaves the trope intact', async ({ page }) => {
    const firstCard = page
      .locator('[class*="border"]')
      .filter({ has: page.getByRole('button', { name: /^Delete$/i }) })
      .first()
    const tropeName = await firstCard.getByRole('link').first().innerText()

    await firstCard.getByRole('button', { name: /^Delete$/i }).click()
    await page.getByRole('button', { name: /Cancel/i }).click()
    await page.waitForTimeout(300)

    await expect(page.getByText(tropeName, { exact: false }).first()).toBeVisible({ timeout: 4_000 })
  })

  test('modal message warns about re-embedding', async ({ page }) => {
    await page.getByRole('button', { name: /^Delete$/i }).first().click()
    await expect(page.getByText(/re-embed/i)).toBeVisible({ timeout: 4_000 })
  })
})

// ── 4. Archetypes — ConfirmModal on delete ────────────────────────────────────

test.describe('Archetypes page — delete confirm modal', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test.beforeEach(async ({ page }) => {
    await page.goto('/archetypes')
    await expect(page).toHaveURL('/archetypes', { timeout: 10_000 })
  })

  test('Delete button exists on at least one archetype card', async ({ page }) => {
    await expect(page.getByRole('button', { name: /^Delete$/i }).first()).toBeVisible({ timeout: 8_000 })
  })

  test('clicking Delete opens a confirmation modal', async ({ page }) => {
    await page.getByRole('button', { name: /^Delete$/i }).first().click()
    await expect(
      page.getByRole('dialog').or(page.locator('[class*="fixed"][class*="inset"]'))
    ).toBeVisible({ timeout: 4_000 })
  })

  test('cancelling the modal leaves the archetype intact', async ({ page }) => {
    const firstCard = page
      .locator('[class*="border"]')
      .filter({ has: page.getByRole('button', { name: /^Delete$/i }) })
      .first()
    const archetypeName = await firstCard.getByRole('link').first().innerText()

    await firstCard.getByRole('button', { name: /^Delete$/i }).click()
    await page.getByRole('button', { name: /Cancel/i }).click()
    await page.waitForTimeout(300)

    await expect(page.getByText(archetypeName, { exact: false }).first()).toBeVisible({ timeout: 4_000 })
  })

  test('modal message warns about re-embedding', async ({ page }) => {
    await page.getByRole('button', { name: /^Delete$/i }).first().click()
    await expect(page.getByText(/re-embed/i)).toBeVisible({ timeout: 4_000 })
  })
})

// ── 5. BookDetail — crowd-tagged badge ────────────────────────────────────────

test.describe('BookDetail — crowd-tagged badge', () => {
  test.skip(!hasAdmin, 'ADMIN_EMAIL not set')

  test('crowd-tagged badge absent on a new book with only one tagged trope', async ({ page }) => {
    // Navigate first so localStorage auth token is available
    await page.goto('/admin')
    await expect(page).toHaveURL('/admin', { timeout: 10_000 })

    const token = await page.evaluate(() => {
      const key = Object.keys(localStorage).find(k => k.startsWith('sb-') && k.endsWith('-auth-token'))
      if (!key) return ''
      try { return (JSON.parse(localStorage.getItem(key) ?? '') as { access_token: string }).access_token } catch { return '' }
    })

    const res = await page.request.post('/api/v1/books/', {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title: `E2E-CrowdBadge-${Date.now()}`,
        author: 'E2E Author',
        isbn: `888${Date.now()}`.slice(0, 13),
        publication_date: '2024-01-01',
        description: 'Crowd badge smoke test book',
      },
    })
    expect(res.ok()).toBeTruthy()
    const { book_id: bookId } = await res.json()

    await page.request.post(`/api/v1/books/${bookId}/tropes`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { trope_id: 1, weight: 0.8 },
    })

    await page.goto(`/books/${bookId}`)
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 8_000 })

    // Only one admin tag — below promotion threshold → no crowd-tagged badge
    await expect(page.getByText('crowd-tagged')).not.toBeVisible({ timeout: 2_000 })

    await page.request.delete(`/api/v1/books/${bookId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  })
})

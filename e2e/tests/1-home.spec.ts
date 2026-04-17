/**
 * Home page — public, no auth required.
 * Tests both the logged-out hero and verifies redirect behaviour for protected routes.
 */

import { test, expect } from '@playwright/test'

test.describe('Home page (logged out)', () => {
  test('shows hero with app name and CTA buttons', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/CommonThread/)
    await expect(page.getByRole('heading', { name: 'CommonThread' }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /Browse Books/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Browse Tropes/i })).toBeVisible()
  })

  test('header shows Sign in and Sign up links when logged out', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Sign up' })).toBeVisible()
  })

  test('protected route /books redirects to /auth/login', async ({ page }) => {
    await page.goto('/books')
    await expect(page).toHaveURL(/\/auth\/login/)
  })

  test('protected route /shelf redirects to /auth/login', async ({ page }) => {
    await page.goto('/shelf')
    await expect(page).toHaveURL(/\/auth\/login/)
  })

  test('protected route /my-tags redirects to /auth/login', async ({ page }) => {
    await page.goto('/my-tags')
    await expect(page).toHaveURL(/\/auth\/login/)
  })

  test('protected route /friends redirects to /auth/login', async ({ page }) => {
    await page.goto('/friends')
    await expect(page).toHaveURL(/\/auth\/login/)
  })

  test('404 page shown for unknown routes', async ({ page }) => {
    await page.goto('/this-does-not-exist-xyz')
    await expect(page.getByText(/404|not found/i).first()).toBeVisible()
  })

  test('/unauthorized page renders 403 message', async ({ page }) => {
    await page.goto('/unauthorized')
    await expect(page.getByText(/403|unauthorized|not allowed/i)).toBeVisible()
  })

  test('TropeDetail page renders without auth', async ({ page }) => {
    await page.goto('/tropes/1')
    // Should show trope name or breadcrumb, not redirect to login
    await expect(page).not.toHaveURL(/\/auth\/login/)
    await expect(page.locator('h1,h2').first()).toBeVisible()
  })

  test('ArchetypeDetail page renders without auth', async ({ page }) => {
    await page.goto('/archetypes/1')
    await expect(page).not.toHaveURL(/\/auth\/login/)
    await expect(page.locator('h1,h2').first()).toBeVisible()
  })
})

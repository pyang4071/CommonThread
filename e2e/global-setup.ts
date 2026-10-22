/**
 * Playwright global setup — runs once before all test suites.
 *
 * Auth strategy (in priority order):
 *   1. If TEST_EMAIL + TEST_PASSWORD are set → UI login form.
 *   2. If TEST_EMAIL + SUPABASE_SERVICE_ROLE_KEY are set → magic-link auth
 *      (no password needed — the service role generates a one-time link).
 *   3. Neither set → writes empty state; auth tests will skip.
 *
 * Same two-step logic applies for ADMIN_EMAIL / ADMIN_PASSWORD.
 *
 * The saved .auth/*.json files hold live sessions; global-teardown.ts revokes
 * and deletes them after the run.
 */

import { chromium } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { revokeAuthFiles } from './global-teardown'

const BASE = 'http://localhost:5173'
const AUTH_DIR = path.join(__dirname, '.auth')

/** UI login: fill email+password form, wait for redirect to /. */
async function loginViaForm(email: string, password: string, file: string) {
  const dest = path.join(AUTH_DIR, file)
  const browser = await chromium.launch()
  const page = await browser.newPage()
  try {
    await page.goto(`${BASE}/auth/login`)
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')
    await page.waitForURL(`${BASE}/`, { timeout: 15_000 })
    await page.context().storageState({ path: dest })
    console.log(`[global-setup] UI login OK for ${email} → ${file}`)
  } catch (e) {
    console.error(`[global-setup] UI login failed for ${email}:`, e)
    fs.writeFileSync(dest, JSON.stringify({ cookies: [], origins: [] }))
  } finally {
    await browser.close()
  }
}

/** Magic-link login: service role generates a link → browser follows it → session saved. */
async function loginViaMagicLink(
  email: string,
  supabaseUrl: string,
  serviceRoleKey: string,
  file: string,
) {
  const dest = path.join(AUTH_DIR, file)

  // Generate a magic link via the Supabase admin API.
  const res = await fetch(`${supabaseUrl}/auth/v1/admin/generate_link`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceRoleKey}`,
      apikey: serviceRoleKey,
    },
    body: JSON.stringify({
      type: 'magiclink',
      email,
      options: { redirect_to: BASE },
    }),
  })

  if (!res.ok) {
    const body = await res.text()
    console.error(`[global-setup] generate_link failed for ${email}: ${res.status} ${body}`)
    fs.writeFileSync(dest, JSON.stringify({ cookies: [], origins: [] }))
    return
  }

  const { action_link } = (await res.json()) as { action_link: string }
  if (!action_link) {
    console.error(`[global-setup] No action_link in response for ${email}`)
    fs.writeFileSync(dest, JSON.stringify({ cookies: [], origins: [] }))
    return
  }

  // Rewrite the redirect_to in the link to point at our dev server.
  const linkUrl = new URL(action_link)
  linkUrl.searchParams.set('redirect_to', BASE)

  const browser = await chromium.launch()
  const page = await browser.newPage()
  try {
    // Follow the magic link — Supabase will verify the token and redirect to BASE.
    await page.goto(linkUrl.toString(), { waitUntil: 'commit' })
    // Wait until we land somewhere on the dev server (not supabase.co).
    await page.waitForURL(/localhost:5173/, { timeout: 20_000 })
    // Wait for the Supabase JS client to process the hash fragment and
    // write the session to localStorage before we snapshot the state.
    await page.waitForFunction(
      () => Object.keys(localStorage).some(
        k => k.startsWith('sb-') && k.endsWith('-auth-token')
      ),
      { timeout: 15_000 },
    )
    await page.context().storageState({ path: dest })
    console.log(`[global-setup] Magic-link login OK for ${email} → ${file}`)
  } catch (e) {
    console.error(`[global-setup] Magic-link login failed for ${email}:`, e)
    fs.writeFileSync(dest, JSON.stringify({ cookies: [], origins: [] }))
  } finally {
    await browser.close()
  }
}

async function saveState(
  email: string | undefined,
  password: string | undefined,
  file: string,
) {
  const dest = path.join(AUTH_DIR, file)

  if (!email) {
    console.warn(`[global-setup] Skipping ${file} — no email set.`)
    fs.writeFileSync(dest, JSON.stringify({ cookies: [], origins: [] }))
    return
  }

  if (password) {
    await loginViaForm(email, password, file)
    return
  }

  const supabaseUrl = process.env.SUPABASE_URL
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (supabaseUrl && serviceRoleKey) {
    await loginViaMagicLink(email, supabaseUrl, serviceRoleKey, file)
    return
  }

  console.warn(`[global-setup] Skipping ${file} — no password or service role key set.`)
  fs.writeFileSync(dest, JSON.stringify({ cookies: [], origins: [] }))
}

export default async function globalSetup() {
  // A run killed before global-teardown leaves live sessions behind — end them first.
  await revokeAuthFiles()
  fs.mkdirSync(AUTH_DIR, { recursive: true })

  await saveState(process.env.TEST_EMAIL, process.env.TEST_PASSWORD, 'user.json')
  await saveState(process.env.ADMIN_EMAIL, process.env.ADMIN_PASSWORD, 'admin.json')
}

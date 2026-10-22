/**
 * Playwright global teardown — runs once after all test suites.
 *
 * Signs out the Supabase sessions global-setup created, then deletes
 * .auth/*.json. Supabase refresh tokens never expire on their own, so without
 * this every run leaves a live session (with a usable refresh token) behind
 * for each test account.
 *
 * global-setup also calls revokeAuthFiles() first, to clean up after a run
 * that was killed before teardown could run.
 */

import * as fs from 'fs'
import * as path from 'path'

const AUTH_DIR = path.join(__dirname, '.auth')

type StoredSession = { ref: string; accessToken: string; refreshToken: string }

/** Pull the Supabase session out of a Playwright storageState file. */
function readSession(file: string): StoredSession | null {
  const state = JSON.parse(fs.readFileSync(file, 'utf8'))
  for (const origin of state.origins ?? []) {
    for (const item of origin.localStorage ?? []) {
      const match = /^sb-(.+)-auth-token$/.exec(item.name)
      if (!match) continue
      const value = JSON.parse(item.value)
      return { ref: match[1], accessToken: value.access_token, refreshToken: value.refresh_token }
    }
  }
  return null
}

/**
 * POST /logout?scope=local ends the session the access token belongs to. If the
 * access token has expired, refresh first. If the browser already rotated the
 * stored refresh token, Supabase's reuse detection revokes the session anyway.
 */
async function revokeSession(session: StoredSession, file: string): Promise<void> {
  const supabaseUrl = process.env.SUPABASE_URL ?? `https://${session.ref}.supabase.co`
  const apiKey = process.env.SUPABASE_ANON_KEY ?? process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!apiKey) {
    console.warn(`[global-teardown] No SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY — cannot revoke ${file}; its session stays live.`)
    return
  }
  const headers = { apikey: apiKey, 'Content-Type': 'application/json' }
  const logout = (token: string) =>
    fetch(`${supabaseUrl}/auth/v1/logout?scope=local`, {
      method: 'POST',
      headers: { ...headers, Authorization: `Bearer ${token}` },
    })

  let res = await logout(session.accessToken)
  if (res.status === 401 || res.status === 403) {
    const refreshed = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=refresh_token`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    })
    if (!refreshed.ok) {
      console.log(`[global-teardown] ${file}: session already ended (${refreshed.status})`)
      return
    }
    res = await logout(((await refreshed.json()) as { access_token: string }).access_token)
  }
  if (res.ok) console.log(`[global-teardown] ${file}: session revoked`)
  else console.warn(`[global-teardown] ${file}: logout failed (${res.status} ${await res.text()})`)
}

/** Revoke and delete every storageState file in .auth/. Never throws. */
export async function revokeAuthFiles(): Promise<void> {
  if (!fs.existsSync(AUTH_DIR)) return
  for (const name of fs.readdirSync(AUTH_DIR).filter(f => f.endsWith('.json'))) {
    const file = path.join(AUTH_DIR, name)
    try {
      const session = readSession(file)
      if (session) await revokeSession(session, name)
    } catch (e) {
      console.warn(`[global-teardown] ${name}: could not revoke —`, e)
    } finally {
      fs.rmSync(file, { force: true })
    }
  }
}

export default async function globalTeardown() {
  await revokeAuthFiles()
}

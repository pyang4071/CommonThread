import { defineConfig, devices } from '@playwright/test'
import * as dotenv from 'dotenv'
import * as path from 'path'

dotenv.config({ path: path.join(__dirname, '.env') })

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,   // serial to avoid flakiness on a single DB/server
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  globalSetup: './global-setup.ts',
  globalTeardown: './global-teardown.ts',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },

  projects: [
    // ── No auth ──────────────────────────────────────────────────────────────
    {
      name: 'public',
      use: { ...devices['Desktop Chrome'] },
      testMatch: ['**/1-home.spec.ts', '**/2-auth.spec.ts'],
    },

    // ── Regular user ─────────────────────────────────────────────────────────
    {
      name: 'user',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/user.json',
      },
      testMatch: [
        '**/3-books.spec.ts',
        '**/4-book-detail.spec.ts',
        '**/5-tropes-archetypes.spec.ts',
        '**/6-shelf.spec.ts',
        '**/7-my-tags.spec.ts',
        '**/8-friends.spec.ts',
        '**/9-profile.spec.ts',
        '**/12-phase5-user.spec.ts',
      ],
    },

    // ── Admin user ────────────────────────────────────────────────────────────
    {
      name: 'admin',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/admin.json',
      },
      testMatch: [
        '**/10-admin.spec.ts',
        '**/11-tagging-threshold.spec.ts',
        '**/12-phase5-admin.spec.ts',
      ],
    },
  ],
})

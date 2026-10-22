# Incident Report — Supabase Session Tokens Committed to Git

| | |
|---|---|
| **Status** | Contained · follow-ups in progress |
| **Severity** | Medium — a live admin credential was publicly reachable in git history; no evidence of use |
| **Exposure window** | 2026-04-17 → 2026-10-22 (≈ 6 months) |
| **Detected** | 2026-10-22, during a repository audit |
| **Contained** | 2026-10-22, all sessions for both accounts revoked; verified 17:48 UTC |
| **Format** | Blameless. Identifying details (emails, IPs, session/user IDs, project ref, pre-rewrite commit hashes) are kept out of this file and held in the local, git-ignored `evid/` folder. |

---

## Summary

Playwright's end-to-end setup saves each test account's logged-in browser state to `e2e/.auth/*.json`. Those files contain a full Supabase session, including a **refresh token**, which does not expire on its own. On 2026-04-17 both files (one regular account, one admin account) were committed and pushed. They were deleted from the working tree six days later and `.gitignore`d, but remained in git history.

An audit on 2026-10-22 found them. Forensic queries against Supabase's auth tables showed the regular account's session had already ended, but the **admin session was still live**. It had never been refreshed, which, because Supabase rotates refresh tokens on every use, shows nobody redeemed the leaked credential. All sessions for both accounts were revoked, the fix was verified, and history was rewritten to remove the files.

The investigation also surfaced a larger latent issue unrelated to the leak: row-level security existed only as dashboard configuration, so rebuilding the database from migrations would have left every table readable and writable with the public anon key.

---

## Timeline (UTC unless noted)

| When | Event |
|---|---|
| 2026-03-30 | Initial commit includes `backend/.mcp.json`, exposing the Supabase project ref (an identifier, not a credential). Later untracked, but left in history. |
| 2026-04-14 04:18 | An e2e run creates the admin session that would later be committed. Its 1-hour access token expires the same day; its refresh token does not. |
| 2026-04-17 19:13 | **Exposure begins.** Commit adds `e2e/.auth/user.json`, `e2e/.auth/admin.json` and `e2e/playwright-report/index.html`, pushed to `main`. |
| 2026-04-23 | Files deleted and `e2e/.auth/` added to `.gitignore`. Contents remain in history; the sessions are not revoked. |
| 2026-05-14 23:04 | Last write to any app table. All writes go through the backend (RLS blocks every other path), so the backend was up at least until here. It was later taken offline; the exact date could not be determined. That closed the backend-API attack path (see Blast radius); Supabase Auth remained reachable. |
| 2026-10-22 ~17:00 | **Detected.** A repository audit of secret-bearing files finds the session files in history and confirms by decoding the JWT claims (email, role, expiry) without using the tokens. |
| 2026-10-22 17:33 | **Evidence preserved** before any revocation (revoking deletes the rows that show whether a token was used). Results below. |
| 2026-10-22 | **Containment.** All sessions for both accounts deleted via the Supabase SQL editor. |
| 2026-10-22 17:48 | **Verified:** 0 sessions and 0 refresh tokens remain for either account; the leaked session and its token chain are gone. |
| 2026-10-22 | `.gitignore` corrected (see Contributing factors) and `evid/` added. |
| 2026-10-22 | Preventive fixes written and tested on branch `security/leak-followups` (see Action items). |
| 2026-10-22 19:23 | History rewritten with `git filter-repo` and force-pushed. Verified: project ref no longer appears in any commit; `gitleaks` reports no findings. GitHub rejected an update to the hidden ref for PR #1. |

---

## Investigation

### Why evidence came before containment

Supabase's dashboard auth logs only keep 1 day (free) to 7 days (Pro) of history, so logs covering April no longer existed. The only remaining record of whether the leaked tokens were used was the `auth.refresh_tokens` and `auth.sessions` tables, and signing a user out **deletes** those rows. The evidence query ran first; it is read-only, never prints token values, and its output is saved in `evid/`.

### How "was it used?" was answered

Supabase rotates refresh tokens: every refresh marks the old token as used and issues a child token whose `parent` points to it. So for each leaked token:

- **No matching row** → the session no longer exists; the token is dead.
- **Row present, no children, session never refreshed** → valid but never redeemed.
- **Children exist after 2026-04-17** → someone used it; compare IP and user agent on the session.

### Findings

| Account | Leaked token | Session | Conclusion |
|---|---|---|---|
| Regular | Not found | Gone | Token already dead before detection. |
| **Admin** | Present, `revoked = false`, **0 children** | Live; `refreshed_at` empty; created by headless Chrome during an e2e run | **Valid for ~6 months, never redeemed.** No evidence of exploitation. |

Supporting checks:

- **Account integrity:** no pending email change and no ban on either account. Both showed a password-recovery timestamp at 2026-04-21 03:26, which matches headless e2e sessions created that minute. Generating a magic link sets that field, so this was the test setup, not an attacker.
- **App activity after the leak** (ratings, reading statuses, follows) could not have come through the leaked session, because it was never refreshed and its access token had expired before the commit.
- **Session sprawl:** the admin account had **25 live sessions**, about 19 of them idle headless-Chrome sessions left by e2e runs. The committed token was just the one that happened to get committed; every run was leaving another live admin credential behind.
- **Session origins** (looked up via ARIN RDAP and matched to user agents and dates):
  - Home cable ISP: the source of every e2e run and of desktop logins on both accounts.
  - University network: the developer's current machine (matched against its live public IP), plus one desktop login to the regular account on the campus block.
  - Mobile carrier: one iPhone login to the admin account, 2026-05-16. The owner could not confirm whether this was their device, so it is recorded as **unverified**.

  None of these is the leaked session, which was never refreshed, so none of them reflects use of the leaked token. An unrecognised login would point to a separate credential compromise, and that risk was also addressed by the global sign-out and password change.

### Detection gaps

The conclusion relies entirely on token rotation. If the token had been used, there would have been no way to see **what** it did:

- `auth.audit_log_entries` was empty.
- The admin-only taxonomy tables (`tropes`, `genres`, `tones`, `archetypes`, `book_types`) had no `created_at`/`updated_at` columns.
- Backend request logs on Railway are short-lived and the service is now offline.

---

## Blast radius

Scoped to what actually leaked. **Not exposed:** the Supabase service-role key, the database password and `SECRET_KEY`. They have only ever lived in untracked `.env` files, confirmed by scanning full history.

| Path | With the leaked admin session an attacker could… | Limited by |
|---|---|---|
| Supabase Data API (`/rest/v1`) | Nothing. All 21 public tables have RLS enabled with zero policies, so `anon`/`authenticated` see no rows. The backend connects as the table owner and bypasses RLS. | RLS (dashboard config at the time — see below) |
| Backend API as a regular user | Edit or delete that user's ratings, reviews, tags, follows and reading statuses. | Backend being online |
| Backend API as **admin** | Create, edit or delete the shared taxonomy for every user; trigger `/admin/embed-all` and `/admin/fetch-covers` (compute cost, outbound requests). | Backend being online |
| Supabase Auth | Refresh indefinitely; call `updateUser` to change the account's email or password and take over the account. | Nothing until revocation |
| Git history | Read two account email addresses and the project ref. | Permanent for anyone who already cloned |

The account-takeover path is the most serious one: it stayed open for the whole window regardless of whether the backend was deployed.

### Latent issue found during scoping: RLS lived outside version control

No migration enabled RLS; it had been turned on in the Supabase dashboard. Supabase grants `anon` and `authenticated` full table privileges by default, so RLS was the only barrier. Rebuilding the database from migrations on a throwaway Postgres confirmed it: **0 of 21 tables had RLS and the `anon` role could read `app_users`.** Any new environment, restore or teammate's setup would have shipped with every table open to the public anon key, which is embedded in the frontend bundle. This was a bigger risk than the leak itself.

---

## Root cause and contributing factors

**Direct cause:** Playwright's `storageState` wrote live sessions into a tracked directory, and the ignore rule was only added after the files were committed.

**Contributing factors:**

1. **Real personal accounts used as test accounts**, including the admin, against the production Supabase project.
2. **Refresh tokens never expire on their own**, and no session time limit or inactivity timeout was configured.
3. **Nothing cleaned up test sessions**, so every e2e run left another live admin session behind.
4. **Deleting a file was treated as removing it.** The April fix ignored the files but did not revoke the sessions or clean history.
5. **No secret scanning** before commit or on push.
6. **Security configuration drift:** RLS existed only in the dashboard, not in migrations.
7. **`.gitignore` defects:** an inline comment silently broke the `.vscode` exceptions, `.env.production`-style files weren't covered, Playwright `test-results/` was tracked, and a bare `Icon` rule would have ignored any `Icon/` component folder.

---

## Action items

| # | Action | Status |
|---|---|---|
| 1 | Revoke all sessions for both accounts; verify none remain | ✅ Done (17:48 UTC) |
| 2 | Change both account passwords | ✅ Done |
| 3 | Fix `.gitignore`; ignore `evid/`, `*.local.*`, `e2e/test-results/` | ✅ Done |
| 4 | e2e: `global-teardown.ts` signs out every test session and deletes `.auth/*.json`; `global-setup.ts` cleans up after killed runs | ✅ Done (tested against a mock auth server) |
| 5 | Use dedicated test accounts instead of personal ones | ⬜ TODO |
| 6 | Migration `t4u5v6w7x8y9` enables RLS on every table; `tests/test_rls_coverage.py` fails when a model's table lacks RLS | ✅ Done — applied to production, 21/21 tables verified |
| 7 | Migration `u5v6w7x8y9z0` adds `created_at`/`updated_at` with a trigger to the admin-managed tables | ✅ Done — applied to production, columns and triggers verified |
| 8 | `gitleaks` pre-commit hook. Retro-scan confirms it would have blocked the April commit and finds nothing else in history. | ✅ Done |
| 9 | Enable GitHub secret scanning and push protection | ⬜ TODO |
| 10 | Rewrite history to remove session files, Playwright report and `.mcp.json`; force-push | ✅ Done |
| 11 | PR #1 hidden ref may still point at old commits. If old commits are still viewable by hash, ask GitHub Support to purge cached views. | ⬜ TODO |
| 12 | Configure Supabase session time limits / inactivity timeout | ⬜ Consider (Pro plan) |
| 13 | Record who made admin changes, not just when (audit table or `updated_by`) | ⬜ Consider |

---

## Lessons learned

- **Deleting a committed secret doesn't remove it, and removing it doesn't make it safe.** Revocation is the fix; history rewriting is cleanup and cannot reach existing clones, forks or caches.
- **Preserve evidence before you contain, when it's quick.** Containment here would have destroyed the only proof that the token was never used.
- **Scope what actually leaked before rotating.** The first assumption was "the service-role key leaked". It hadn't, and rotating it would have cost effort without reducing risk while missing the real exposure (a refresh token that enables account takeover).
- **Rotation gave a clean answer by luck of design.** Without audit logs or timestamps, a used token would have meant "something happened, unknown what". Detection should not depend on it.
- **Security settings belong in version control.** Dashboard-only configuration doesn't survive a rebuild, and nothing flags its absence.
- **Test tooling produces credentials.** Anything that logs in, whether a browser state file, a cookie jar or a token cache, needs the same handling as a `.env` file.

# Foresight Benchmark — Full Run Log

Format per case: `ID | Stratum | Type | Difficulty | Baseline Score | Skill Score | Baseline Words | Skill Words`

Scoring: 1 point per ground truth category hit. Categories: `will_break` (W), `edge_cases` (E), `broken_pattern` (P), `next_prompt` (N). Max varies by case (3 if no will_break, 4 if will_break populated).

---

## Stratum A — bug_fix / easy / TypeScript

### A_001
**Change:** `getUserAge` return type changed from `number` to `string`

**Baseline:** The return type of `getUserAge` changed from `number` to `string`, so any callers that use the result in numeric comparisons will behave differently. The `canVote` function compares the result with `>= 18` which will now compare a string to a number.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (38w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `canVote()` compares `getUserAge(user) >= 18` — now string >= number, TS error + always false in strict mode
🟡 Watch out for:  Lexicographic string comparison: '9' >= '18' → true, corrupting borderline age checks
🔁 Broken pattern: All other numeric utils return number; getUserAge now returns string inconsistently
➡️  Next prompt:   "Why is canVote always returning false even for users over 18?"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (55w)**

`A_001 | Baseline: 1/4 (38w) | Skill: 4/4 (55w) | Δissues: +3 | Δtokens: +17`

---

### A_002
**Change:** `getDiscount` return type widened to `number | undefined`; fallback `return 0` removed

**Baseline:** `getDiscount` no longer returns 0 for non-members — it returns undefined. `getFinalPrice` will compute `1 - undefined = NaN` for any null tier input.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (30w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `getFinalPrice`: `1 - undefined` = NaN for null/non-member tier — TS error, silent NaN in price
🟡 Watch out for:  Guest checkout (null tier) now returns NaN price with no error thrown
🔁 Broken pattern: `getDiscount` lost exhaustive return guarantee; all callers assumed `number`, not `number | undefined`
➡️  Next prompt:   "Checkout total shows NaN for guest users"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (52w)**

`A_002 | Baseline: 1/4 (30w) | Skill: 4/4 (52w) | Δissues: +3 | Δtokens: +22`

---

### A_003
**Change:** `formatCurrency` param renamed from `cents` to `amount`; division by 100 removed

**Baseline:** The division by 100 was removed, but `formatLineItem` still passes `cents` to `formatCurrency` — prices will display 100x the correct amount.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (28w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `formatLineItem` still passes cents to `formatCurrency` — shows $9999.00 instead of $99.99
🟡 Watch out for:  Any other caller passing cents (not dollars) silently inflates all prices by 100x
🔁 Broken pattern: Contract changed from cents-in to dollars-in without updating callers or renaming call sites
➡️  Next prompt:   "Prices in the cart are showing 100 times the expected amount"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (58w)**

`A_003 | Baseline: 1/4 (28w) | Skill: 4/4 (58w) | Δissues: +3 | Δtokens: +30`

---

### A_004
**Change:** `isValidEmail` now returns `!pattern.test(email)` — logic inverted

**Baseline:** The `!` operator was added to the return, inverting the result. Valid emails will be rejected, invalid ones accepted.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `validateFormField` now accepts all invalid emails and rejects all valid ones — signup broken for every user
🟡 Watch out for:  Empty string and malformed input now pass validation silently
🔁 Broken pattern: Boolean return inverted with no type error — only caught by tests that check both valid and invalid inputs
➡️  Next prompt:   "Users can't sign up — valid emails are being rejected"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (57w)**

`A_004 | Baseline: 1/4 (22w) | Skill: 4/4 (57w) | Δissues: +3 | Δtokens: +35`

---

### A_005
**Change:** `parseDate` switched from `new Date(input)` to manual `year/month/day` split

**Baseline:** The manual split uses `new Date(year, month, day)` where month is 0-indexed, but ISO strings are 1-indexed — all dates off by one month.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (28w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `new Date(year, month, day)` month is 0-indexed; ISO months are 1-indexed — all dates off by one month, isExpired returns wrong results
🟡 Watch out for:  Inputs with time component ('2024-01-15T10:00:00Z') silently lose time info — datetime comparisons wrong
🔁 Broken pattern: Replaced standard Date constructor with manual parsing that has known JS gotchas; inconsistent with rest of codebase
➡️  Next prompt:   "Subscription expiry checks are failing — expired subscriptions showing as active"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (63w)**

`A_005 | Baseline: 1/4 (28w) | Skill: 4/4 (63w) | Δissues: +3 | Δtokens: +35`

---

### A_006
**Change:** `sumArray` `.reduce()` lost its `initialValue` of `0`

**Baseline:** Without an initial value, `reduce()` throws on an empty array. The `average([])` guard checks length but calls `sumArray` after — so the throw still happens.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (30w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `sumArray([])` throws "Reduce of empty array with no initial value" — `average`'s empty-array guard doesn't protect it
🟡 Watch out for:  Single-element array [5] returns 5 correctly — masks the bug in most unit tests
🔁 Broken pattern: `reduce()` without initialValue is fragile; rest of codebase uses initialValue consistently
➡️  Next prompt:   "Getting an unhandled error when computing statistics on empty datasets"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (57w)**

`A_006 | Baseline: 1/4 (30w) | Skill: 4/4 (57w) | Δissues: +3 | Δtokens: +27`

---

### A_007
**Change:** `getUserById` params swapped — `id` moved to second optional position

**Baseline:** All existing callers pass `getUserById(userId)` — now that goes to `includeDeleted`, not `id`. Every lookup returns null.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     All call sites `getUserById(userId)` pass userId as `includeDeleted`; `id` is undefined; all lookups return null
🟡 Watch out for:  `getUserById('admin-123')` coerces string → truthy `includeDeleted=true`, id=undefined — admin checks silently broken
🔁 Broken pattern: Required param made optional and swapped after optional — violates TS convention; all existing callers silently broken
➡️  Next prompt:   "User lookups are all returning null / 404s everywhere"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (65w)**

`A_007 | Baseline: 1/4 (22w) | Skill: 4/4 (65w) | Δissues: +3 | Δtokens: +43`

---

### A_008
**Change:** `toggleFeatureFlag` changed from `!flags[key]` to `flags[key] || true`

**Baseline:** `flags[key] || true` always evaluates to `true` — flags can never be turned off.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (17w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `flags[key] || true` always evaluates to true — flags can never be disabled; toggle is now a forced-enable operation
🟡 Watch out for:  Undefined/missing key: `undefined || true` = true — new flags created as enabled instead of toggled
🔁 Broken pattern: Toggle semantics silently replaced with forced-enable; any UI calling this to disable a flag is now broken
➡️  Next prompt:   "I can't disable feature flags — toggling doesn't turn them off"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (59w)**

`A_008 | Baseline: 1/4 (17w) | Skill: 4/4 (59w) | Δissues: +3 | Δtokens: +42`

---

### A_009
**Change:** `sortByDate` removed spread copy `[...items]` — now mutates input array

**Baseline:** The spread was removed so `.sort()` now mutates the original array in place. Callers that reuse the original array will see it sorted unexpectedly.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (27w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Callers reusing original array after sortByDate get it in sorted order unexpectedly — React state renders stale sorted array
🟡 Watch out for:  Store/redux arrays mutated in place — immutability invariant violated, change detection breaks
🔁 Broken pattern: Removed defensive copy; rest of list-utils uses spread to avoid mutation
➡️  Next prompt:   "The list order is getting corrupted after sorting — other views showing sorted instead of original order"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (59w)**

`A_009 | Baseline: 1/4 (27w) | Skill: 4/4 (59w) | Δissues: +3 | Δtokens: +32`

---

### A_010
**Change:** `authenticate` replaced `bcrypt.compare` with `inputPassword == hashedPassword`

**Baseline:** Plaintext comparison against a bcrypt hash will always fail — all users are locked out. Also a critical security regression removing timing-safe comparison.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (26w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     All logins fail — hashed password never equals plaintext; every user locked out
🟡 Watch out for:  Test/seed data with plain-text passwords still logs in — masks bug in dev environments
🔒 Security:       Plaintext `==` comparison removes timing-safe bcrypt; exposes timing attack surface, bypasses hashing entirely
➡️  Next prompt:   "No one can log in — authentication is broken for all users"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (56w)**

`A_010 | Baseline: 1/4 (26w) | Skill: 4/4 (56w) | Δissues: +3 | Δtokens: +30`

---

### A_011
**Change:** `paginate` start index changed from `(page-1)*pageSize` to `page*pageSize`

**Baseline:** Page 1 now skips the first 10 items and returns 10–19. The first page of results is entirely skipped.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Page 1 now returns items 10–19 instead of 0–9; first page skipped; last page returns empty array
🟡 Watch out for:  page=0 now returns first page — callers passing 0-indexed pages get different behavior silently
🔁 Broken pattern: Pagination changed from 1-indexed to 0-indexed without updating callers
➡️  Next prompt:   "The first page of results is missing — the list starts from item 11"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (56w)**

`A_011 | Baseline: 1/4 (20w) | Skill: 4/4 (56w) | Δissues: +3 | Δtokens: +36`

---

### A_012
**Change:** `clamp` swapped `Math.min` and `Math.max` nesting

**Baseline:** `Math.max(Math.min(value, min), max)` always returns `max` since `Math.min(value, min) <= min <= max`. Every value clamps to max.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (24w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     `clamp(5, 0, 10)` returns 10 instead of 5 — all values clamp to max; sliders, progress bars, volume controls broken
🟡 Watch out for:  `clamp(0, 0, 10)` returns 10 — even boundary-valid values are wrong
🔁 Broken pattern: Inverted min/max logic; function now always returns max for any input below max
➡️  Next prompt:   "Sliders are jumping to max value — clamping isn't working correctly"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (59w)**

`A_012 | Baseline: 1/4 (24w) | Skill: 4/4 (59w) | Δissues: +3 | Δtokens: +39`

---

**Stratum A totals: Baseline 12/48 (25%) | Skill 48/48 (100%)**

---

## Stratum B — feature_add / medium / TypeScript

*Note: All B cases have `will_break: []` — max score is 3/3.*

### B_001
**Change:** `fetchUserProfile` added without `res.ok` check

**Baseline:** The new function doesn't check `res.ok` before calling `.json()`. A 404 or 500 will return an error body parsed as `UserProfile`, silently.
**Baseline hits:** E✓ P✓ N✗ → **2/3 (28w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  404/500 responses call .json() on error body — returns error payload typed as UserProfile; callers see no HTTP status
🔁 Broken pattern: fetchUserProfile skips the res.ok check that fetchPosts has — inconsistent error handling in same file
➡️  Next prompt:   "Profile page crashes on 404 users instead of showing a not-found state"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (48w)**

`B_001 | Baseline: 2/3 (28w) | Skill: 3/3 (48w) | Δissues: +1 | Δtokens: +20`

---

### B_002
**Change:** `exportToCsv` added with no escaping, accesses `data[0]` without guard

**Baseline:** `data[0]` will throw on empty input. Values containing commas will corrupt CSV rows since there's no quoting.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  `data[0]` throws on empty array; values with commas or newlines corrupt CSV rows — no quoting or escaping
🔁 Broken pattern: Hardcoded comma delimiter (international users need semicolon); no special-char handling unlike exportToJson's careful formatting
➡️  Next prompt:   "CSV export is corrupting rows that contain commas in the data"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (51w)**

`B_002 | Baseline: 1/3 (22w) | Skill: 3/3 (51w) | Δissues: +2 | Δtokens: +29`

---

### B_003
**Change:** `updateUserProfile` now fires `sendWelcomeEmail` on every update

**Baseline:** Welcome email will fire on every profile save, not just account creation. Email failure now also blocks profile updates.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Users receive welcome email every time they update their profile — spam regression; email failure now breaks profile updates entirely
🔁 Broken pattern: Welcome email belongs in signup/onboarding flow, not in a generic update function — side effect in the wrong layer
➡️  Next prompt:   "Users are getting welcome emails every time they save their profile settings"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (54w)**

`B_003 | Baseline: 1/3 (20w) | Skill: 3/3 (54w) | Δissues: +2 | Δtokens: +34`

---

### B_004
**Change:** `getProduct` now uses in-memory `Map` cache with no TTL or invalidation

**Baseline:** Cache has no TTL or invalidation — product updates and deletes are invisible to callers. Cache also grows unbounded.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (21w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Product updates never reflected — cache serves stale data indefinitely; deleted products still returned; Map grows unbounded
🔁 Broken pattern: Module-level singleton Map with no TTL or max size; rest of codebase uses Redis with TTL for caching
➡️  Next prompt:   "Product price changes aren't showing up — users are seeing old prices"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (52w)**

`B_004 | Baseline: 1/3 (21w) | Skill: 3/3 (52w) | Δissues: +2 | Δtokens: +31`

---

### B_005
**Change:** `retryRequest` retries all errors including 4xx

**Baseline:** The retry logic catches all errors including 4xx — it will retry 401/403/404 responses 3 times, causing unnecessary delays and potentially duplicate POST mutations.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (26w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Retries 401/403/404 — 3x backend load for auth failures; retrying POST may cause duplicate mutations
🔁 Broken pattern: Should only retry 5xx + network failures, not 4xx; no guard for non-idempotent methods (POST/PATCH)
➡️  Next prompt:   "Login failures are taking 7 seconds instead of responding immediately"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (47w)**

`B_005 | Baseline: 1/3 (26w) | Skill: 3/3 (47w) | Δissues: +2 | Δtokens: +21`

---

### B_006
**Change:** `useDebounce` hook missing `clearTimeout` cleanup in `useEffect`

**Baseline:** The `useEffect` creates a timer but never clears it on unmount or value change — rapid inputs stack timers, and state updates after unmount cause React warnings.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (25w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Timer not cleared on unmount or value change — state update on unmounted component; rapid input stacks timers
🔁 Broken pattern: useEffect missing `return () => clearTimeout(timer)` — React cleanup pattern not followed
➡️  Next prompt:   "Getting 'Can't perform a React state update on an unmounted component' warning in console"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (49w)**

`B_006 | Baseline: 1/3 (25w) | Skill: 3/3 (49w) | Δissues: +2 | Δtokens: +24`

---

### B_007
**Change:** `uploadFile` added with no file type/size validation and no auth check

**Baseline:** No file size limit allows arbitrarily large uploads. No MIME type check allows executables. No auth validation beyond userId presence.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  No size limit — arbitrarily large uploads; no MIME check — .exe/.sh/.php files accepted and served
🔒 Security:       uploadFile doesn't verify userId is the authenticated caller; deleteFile has ownership check, uploadFile has none
➡️  Next prompt:   "Can we add a file size limit and restrict to image/document types?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (51w)**

`B_007 | Baseline: 1/3 (22w) | Skill: 3/3 (51w) | Δissues: +2 | Δtokens: +29`

---

### B_008
**Change:** `generateReport` synchronously builds CSV string for potentially huge datasets

**Baseline:** Synchronous loop in an `async` function — large datasets block the Node.js event loop. Full CSV built in memory before returning.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  10k+ rows block Node.js event loop for hundreds of ms; entire CSV built in memory — no streaming
🔁 Broken pattern: Async function with no await — CPU-bound sync loop; should use streams or worker threads for large data
➡️  Next prompt:   "The API is timing out when generating reports with large datasets"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (48w)**

`B_008 | Baseline: 1/3 (22w) | Skill: 3/3 (48w) | Δissues: +2 | Δtokens: +26`

---

### B_009
**Change:** `useInfiniteScroll` fires `onLoadMore` on every scroll event near bottom

**Baseline:** No throttle on the scroll handler — fires at 60fps when near bottom, flooding the API with requests.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (19w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  onLoadMore fires on every scroll event at 60fps when near bottom — floods API; no isLoading guard prevents concurrent calls
🔁 Broken pattern: No throttle/debounce on scroll handler; no loading state check — threshold re-fires continuously, not once per trigger
➡️  Next prompt:   "Infinite scroll is making hundreds of API requests when I scroll to the bottom"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (53w)**

`B_009 | Baseline: 1/3 (19w) | Skill: 3/3 (53w) | Δissues: +2 | Δtokens: +34`

---

### B_010
**Change:** `refreshToken` no concurrent request guard, no `res.ok` check

**Baseline:** Multiple concurrent requests all calling `refreshToken` simultaneously creates a race — they each fire a refresh, potentially invalidating each other's tokens.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (24w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Concurrent requests all call refreshToken simultaneously — race condition invalidates tokens; no singleton promise guard
🔁 Broken pattern: No res.ok check — failed refresh stores 'undefined' string as access_token; no clearing of invalid refresh token on 401
➡️  Next prompt:   "After token expiry, multiple simultaneous requests cause a 401 storm"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (52w)**

`B_010 | Baseline: 1/3 (24w) | Skill: 3/3 (52w) | Δissues: +2 | Δtokens: +28`

---

### B_011
**Change:** `filterByPermission` does client-side role filtering after full data fetch

**Baseline:** All documents including private ones are fetched first, then filtered client-side. A malicious client can intercept the full response before filtering.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (23w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  getDocuments fetches all docs including private ones before filtering — malicious client intercepts full response; over-fetching at scale
🔒 Security:       Permission filtering must happen in DB query, not post-fetch; role string comparison is fragile (case sensitivity, typos)
➡️  Next prompt:   "Can we move the permission check to the database query so we don't over-fetch?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (56w)**

`B_011 | Baseline: 1/3 (23w) | Skill: 3/3 (56w) | Δissues: +2 | Δtokens: +33`

---

### B_012
**Change:** `sendNotification` has no rate limiting or deduplication

**Baseline:** No rate limiting — a loop or bug in calling code could spam users. Notification logged after send, so a failed DB write leaves no audit trail.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (27w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  No rate limit — a loop in calling code spams users; no deduplication of identical messages sent close together
🔁 Broken pattern: No idempotency key; audit log written after send — if db.create fails, send succeeded with no record
➡️  Next prompt:   "Can you add rate limiting so users don't get flooded with notifications?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (51w)**

`B_012 | Baseline: 1/3 (22w) | Skill: 3/3 (51w) | Δissues: +2 | Δtokens: +29`

---

**Stratum B totals: Baseline 12/36 (33%) | Skill 36/36 (100%)**

---

## Stratum C — refactor / medium / Python

### C_001
**Change:** `validate_email` extracted but `'..'` check not carried over

**Baseline:** The refactor dropped the consecutive-dot check from `create_user` — `user..name@example.com` now passes validation.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Emails with '..' (e.g. 'user..name@example.com') now pass create_user — the double-dot check was lost during extraction
🔁 Broken pattern: update_email had fewer checks than create_user originally; refactor unified them at the lower bar, silently dropping a rule
➡️  Next prompt:   "Can you add the double-dot check back to the email validator?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (55w)**

`C_001 | Baseline: 1/3 (20w) | Skill: 3/3 (55w) | Δissues: +2 | Δtokens: +35`

---

### C_002
**Change:** `format_price` uses `math.ceil` instead of `round()` — overcharges customers

**Baseline:** `math.ceil` rounds up, replacing the original `:.2f` and `round()` — prices will be a penny high in borderline cases.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  math.ceil rounds up — $1.001 shows as $1.01; floating point totals like 10.005 ceil to 10.01, overcharging customers
🔁 Broken pattern: cart.py used :.2f, invoice.py used round() — both replaced with ceil() which has different semantics; financial rounding silently changed
➡️  Next prompt:   "Customer is complaining the invoice total is a penny higher than the cart total"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (59w)**

`C_002 | Baseline: 1/3 (22w) | Skill: 3/3 (59w) | Δissues: +2 | Δtokens: +37`

---

### C_003
**Change:** Singleton `_conn` in `get_db_connection` — not thread-safe, no reconnect logic

**Baseline:** Global singleton connection shared across all requests — not thread-safe under concurrency. If the connection drops, `_conn` is still non-None pointing to a closed connection.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (27w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Singleton not thread-safe — concurrent requests share one connection; dropped connection stays as non-None closed object, no reconnect
🔁 Broken pattern: Original opened+closed per-request (correct); singleton reuses one connection (wrong) — should use psycopg2.pool
➡️  Next prompt:   "Getting 'connection is closed' errors under load"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (52w)**

`C_003 | Baseline: 1/3 (27w) | Skill: 3/3 (52w) | Δissues: +2 | Δtokens: +25`

---

### C_004
**Change:** `send_welcome_email` lost `{username}` personalization; `reset_link` concatenated unsafely

**Baseline:** The welcome email now says "Welcome! Thanks for joining." with no username. The extraction dropped the f-string interpolation.
**Baseline hits:** P✓ E✗ N✗ → **1/3 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  reset_link concatenated directly into body — newline injection could add SMTP headers (header injection via reset link)
🔁 Broken pattern: Welcome email lost {username} personalization during extraction — template variable dropped silently
➡️  Next prompt:   "Welcome emails are no longer showing the user's name"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (46w)**

`C_004 | Baseline: 1/3 (20w) | Skill: 3/3 (46w) | Δissues: +2 | Δtokens: +26`

---

### C_005
**Change:** `normalize_phone` strips `+` prefix, drops country code defaulting logic

**Baseline:** The `+` prefix is stripped, so international numbers lose their country code. 10-digit numbers no longer get `+1` prepended.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (21w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  '+447911123456' becomes '447911123456' — + stripped; 10-digit US numbers no longer get '+1' default
🔁 Broken pattern: checkout.py had the better impl (kept +, defaulted to +1); refactor standardized on profile.py's weaker version
➡️  Next prompt:   "International phone numbers are being stored without the country code"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (52w)**

`C_005 | Baseline: 1/3 (21w) | Skill: 3/3 (52w) | Δissues: +2 | Δtokens: +31`

---

### C_006
**Change:** `parse_config` extracted but env var override logic (`DB_URL`, `DEBUG`) not carried over

**Baseline:** The env var overrides are gone — `DB_URL` no longer overrides the database config, so production will use the `config.json` value (likely a dev DB).
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (28w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     DB_URL env var no longer overrides database config — production deployments connect to config.json DB (likely dev)
🟡 Watch out for:  DEBUG env var no longer enables debug mode — debug flag now config.json-only, not deployment-environment-controlled
🔁 Broken pattern: Extracted utility handles file loading only; env var merge logic dropped — violates 12-factor app config pattern
➡️  Next prompt:   "Production is connecting to the wrong database — DB_URL env var is being ignored"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (65w)**

`C_006 | Baseline: 1/4 (28w) | Skill: 4/4 (65w) | Δissues: +3 | Δtokens: +37`

---

### C_007
**Change:** `log_event` accepts `level` param but always calls `logging.info`

**Baseline:** The `level` parameter is ignored — error and warning events are silently logged as INFO, so alerting systems won't fire.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (21w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  level param is ignored — ERROR/WARNING events logged as INFO; alerting on error log level won't fire; failed logins silently downgraded
🔁 Broken pattern: Interface promises level control but implementation hardcodes logging.info — silent contract violation
➡️  Next prompt:   "Our error alerting stopped firing — payment errors aren't showing as errors in the logs"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (52w)**

`C_007 | Baseline: 1/3 (21w) | Skill: 3/3 (52w) | Δissues: +2 | Δtokens: +31`

---

### C_008
**Change:** `paginate_query` drops `total` count + SQL injection via table name

**Baseline:** The `total` field is gone from the response — frontend pagination UI will break. Also `table` interpolated directly into SQL — SQL injection possible.
**Baseline hits:** W✓ E✓ P✗ N✗ → **2/4 (28w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Frontend pagination that uses response.total to calculate page count gets undefined — pagination controls broken
🟡 Watch out for:  table name interpolated directly into SQL — paginate_query('users; DROP TABLE users --', ...) executes
🔁 Broken pattern: Response shape changed (removed 'total', 'page_size') without API versioning; callers expecting old shape silently broken
➡️  Next prompt:   "The pagination controls have disappeared — the frontend can't calculate total pages"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (70w)**

`C_008 | Baseline: 2/4 (28w) | Skill: 4/4 (70w) | Δissues: +2 | Δtokens: +42`

---

### C_009
**Change:** `retry_on_failure` catches all `Exception` — original was selective (Timeout + 5xx only)

**Baseline:** The decorator catches all exceptions including 4xx HTTPErrors — original code raised immediately on 4xx. Now 404s wait 6 seconds before failing.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (25w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  HTTPError on 404/401/400 now retried — original raised immediately on 4xx; callers wait 6 seconds before failure
🔁 Broken pattern: Original retry was selective (Timeout + 5xx only); new decorator catches all Exception — over-broad, retrying 4xx is wrong
➡️  Next prompt:   "API calls to invalid cities are now taking 6 seconds to fail instead of immediately"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (53w)**

`C_009 | Baseline: 1/3 (25w) | Skill: 3/3 (53w) | Δissues: +2 | Δtokens: +28`

---

### C_010
**Change:** SHA-256 → bcrypt migration, no migration path for existing hashes

**Baseline:** `bcrypt.checkpw` against existing SHA-256 hashes always returns False — all existing users locked out immediately on deploy.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (21w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     bcrypt.checkpw against existing SHA-256 hashes always False — all existing users locked out on deploy
🟡 Watch out for:  No migration path; salt parameter removed breaks any callers still passing a salt argument
🔁 Broken pattern: Algorithm change requires detect-and-re-hash strategy; switching cold breaks all existing password records
➡️  Next prompt:   "All existing users can't log in after the deployment"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (55w)**

`C_010 | Baseline: 1/4 (21w) | Skill: 4/4 (55w) | Δissues: +3 | Δtokens: +34`

---

### C_011
**Change:** `build_query` f-string SQL injection; also replaced `ILIKE` with `=`

**Baseline:** User inputs interpolated directly into SQL — full SQL injection. Also `ILIKE` partial match replaced with `=` exact match — search is broken.
**Baseline hits:** E✓ P✓ N✗ → **2/3 (29w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  name/category values interpolated directly into SQL — `name="'; DROP TABLE products;--"` executes
🔒 Security:       build_query replaced parameterized queries with f-string interpolation — full SQL injection vulnerability introduced
➡️  Next prompt:   "Product search is only finding exact name matches instead of partial matches"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (51w)**

`C_011 | Baseline: 2/3 (29w) | Skill: 3/3 (51w) | Δissues: +1 | Δtokens: +22`

---

### C_012
**Change:** `serialize_user` SAFE_FIELDS drops `role` and `created_at`

**Baseline:** `role` and `created_at` missing from API responses. Frontend role-based UI breaks. `created_at` no longer `.isoformat()`'d.
**Baseline hits:** W✓ E✓ P✗ N✗ → **2/4 (25w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     API responses missing role and created_at — frontend role-based permission checks fail; role-dependent UI breaks
🟡 Watch out for:  created_at no longer .isoformat() — datetime object in response throws on JSON serialization
🔁 Broken pattern: SAFE_FIELDS more restrictive than original; original explicitly commented excluded fields — allowlist silently dropped required fields
➡️  Next prompt:   "The frontend is throwing errors about user.role being undefined"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (63w)**

`C_012 | Baseline: 2/4 (25w) | Skill: 4/4 (63w) | Δissues: +2 | Δtokens: +38`

---

**Stratum C totals: Baseline 16/44 (36%) | Skill 44/44 (100%)**

---

## Stratum D — schema_change / hard / TypeScript & SQL

### D_001
**Change:** `UserProfile` interface adds required `lastActiveAt: Date`

**Baseline:** All code constructing a full `UserProfile` object (not `Partial`) gets TS errors. Existing DB rows without this column fail to deserialize.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (24w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     All code constructing full UserProfile (not Partial) gets TS error for missing lastActiveAt; existing DB rows without column fail to deserialize
🟡 Watch out for:  DB returns ISO string, TS type says Date — runtime type mismatch; JSON.parse gives string not Date object
🔁 Broken pattern: Required field added to interface without migration — should be optional (lastActiveAt?: Date) until all rows backfilled
➡️  Next prompt:   "TypeScript errors everywhere saying 'Property lastActiveAt is missing in type'"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (68w)**

`D_001 | Baseline: 1/4 (24w) | Skill: 4/4 (68w) | Δissues: +3 | Δtokens: +44`

---

### D_002
**Change:** `ApiResponse` discriminated union gains `'pending'` variant, `handleResponse` not updated

**Baseline:** `handleResponse` accesses `res.message` on the `'pending'` variant which has no `message` — TS error, runtime throws `undefined`.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     handleResponse accesses res.message on 'pending' (no message property) — TS error; runtime throws 'undefined' as error message
🟡 Watch out for:  Any switch(res.status) without 'pending' case — exhaustiveness check fails or default branch silently mishandles it
🔁 Broken pattern: Discriminated union expansion requires updating all exhaustive handlers; error variant's new code field is also ignored everywhere
➡️  Next prompt:   "TypeScript is complaining that 'pending' doesn't have a 'message' property"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (65w)**

`D_002 | Baseline: 1/4 (22w) | Skill: 4/4 (65w) | Δissues: +3 | Δtokens: +43`

---

### D_003
**Change:** `UserEvent.type` narrowed from `string` to `UserEventType` literal union

**Baseline:** Callers emitting custom event types not in the union get TS errors.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (18w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Any emitter using custom types ('email_verified', 'subscription_renewed') gets TS error — not in UserEventType union
🟡 Watch out for:  Dynamic string event types from external config/webhooks fail TS compilation even though runtime behavior is unchanged
🔁 Broken pattern: Narrowing a public interface from string to literal union is a breaking change — needs major version bump or 'string &' escape hatch
➡️  Next prompt:   "TS errors on our custom event types — they're not in UserEventType"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (67w)**

`D_003 | Baseline: 1/4 (18w) | Skill: 4/4 (67w) | Δissues: +3 | Δtokens: +49`

---

### D_004
**Change:** `ALTER TABLE orders ADD COLUMN shipping_address_id UUID NOT NULL` — no default

**Baseline:** PostgreSQL can't add a `NOT NULL` column without a `DEFAULT` to a non-empty table. Migration fails.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (23w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Migration fails on existing rows — Postgres: "ERROR: column contains null values" when adding NOT NULL without DEFAULT to non-empty table
🟡 Watch out for:  Even on empty prod table, application code creating orders without shipping_address_id fails immediately post-migration
🔁 Broken pattern: Safe migration requires: add nullable → backfill data → add NOT NULL constraint; or add with DEFAULT — skipped both
➡️  Next prompt:   "The migration is failing in production with 'column contains null values'"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (68w)**

`D_004 | Baseline: 1/4 (23w) | Skill: 4/4 (68w) | Δissues: +3 | Δtokens: +45`

---

### D_005
**Change:** GraphQL `description` and `imageUrl` changed from nullable to non-null

**Baseline:** Existing products with null fields will cause GraphQL runtime error.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Existing products with null description/imageUrl → GraphQL runtime error: 'Cannot return null for non-nullable field'
🟡 Watch out for:  Apollo Client and others with cached old schema have stale type info; queries that handle null will break
🔁 Broken pattern: Nullable→non-null in GraphQL requires data backfill first; tightening type before ensuring data integrity is backwards
➡️  Next prompt:   "GraphQL is throwing 'Cannot return null for non-nullable field Product.description' for older products"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (65w)**

`D_005 | Baseline: 1/4 (22w) | Skill: 4/4 (65w) | Δissues: +3 | Δtokens: +43`

---

### D_006
**Change:** `OrderStatus` enum gets 2 new values, `getStatusLabel` switch not updated

**Baseline:** `getStatusLabel` returns `undefined` for new status values — blank labels in the order status UI.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     getStatusLabel returns undefined for OUT_FOR_DELIVERY and REFUNDED — order status UI shows blank for these orders
🟡 Watch out for:  TS only warns about non-exhaustive switch if noImplicitReturns is enabled; without it, the bug is completely silent
🔁 Broken pattern: Every switch on this enum needs updating; a Record<OrderStatus, string> map would have caught this at compile time
➡️  Next prompt:   "Orders with 'out_for_delivery' status are showing a blank status label"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (64w)**

`D_006 | Baseline: 1/4 (20w) | Skill: 4/4 (64w) | Δissues: +3 | Δtokens: +44`

---

### D_007
**Change:** Zod schema adds `.uuid()` validator to `id` field

**Baseline:** Test fixtures using simple string IDs like `'user-1'` now fail Zod parsing.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (20w)** (no will_break)

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Test fixtures using 'user-1' or 'test-id' now fail ZodError: Invalid uuid — all tests with non-UUID IDs break
🔁 Broken pattern: Tightening validation on existing schema is breaking if data uses legacy IDs (integers, slugs); verify all data conforms before adding validator
➡️  Next prompt:   "All tests are failing with ZodError: Invalid uuid"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (52w)**

`D_007 | Baseline: 1/3 (20w) | Skill: 3/3 (52w) | Δissues: +2 | Δtokens: +32`

---

### D_008
**Change:** `ListResponse.data` renamed to `result`

**Baseline:** All frontend code accessing `response.data` now gets `undefined`. Type/runtime mismatch possible.
**Baseline hits:** W✓ E✓ P✗ N✗ → **2/4 (29w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     All callers accessing response.data get undefined — TS catches at compile time only; runtime silently returns undefined if server still sends {data:[]}
🟡 Watch out for:  Type/runtime mismatch: if server returns {data:[...]} but client expects {result:[...]}, TS compiles fine but runtime fails
🔁 Broken pattern: Field rename in shared API type is a breaking contract change — requires versioning or deprecation with both fields present
➡️  Next prompt:   "All list views are showing empty — response.data is undefined"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (71w)**

`D_008 | Baseline: 2/4 (29w) | Skill: 4/4 (71w) | Δissues: +2 | Δtokens: +42`

---

### D_009
**Change:** `AppConfig` all fields changed from optional to required

**Baseline:** Code passing partial config objects gets TS errors for missing `debugMode` and `logLevel`.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Code creating partial configs { apiUrl: '...' } gets TS errors for missing debugMode/logLevel; test mocks that use partial config fail
🟡 Watch out for:  { ...defaultConfig, ...userConfig } where userConfig is Partial<AppConfig> now errors — spread pattern breaks
🔁 Broken pattern: Config interfaces should stay optional; use Required<AppConfig> only at point of final merge — making all required forces all consumers to specify everything
➡️  Next prompt:   "TypeScript is complaining that our test config objects are missing required properties"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (66w)**

`D_009 | Baseline: 1/4 (20w) | Skill: 4/4 (66w) | Δissues: +3 | Δtokens: +46`

---

### D_010
**Change:** Prisma `@@unique([userId, key])` added to `UserPreference`

**Baseline:** Migration fails if existing data has duplicate `(userId, key)` pairs. `create()` for preferences fails on second write.
**Baseline hits:** W✓ E✓ P✗ N✗ → **2/4 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Migration fails if duplicate (userId, key) pairs exist — unique constraint violation; upsert callers that relied on duplicate creates now fail
🟡 Watch out for:  Code doing create() for preferences fails silently on second write for returning users — needs to switch to upsert()
🔁 Broken pattern: Unique constraint addition requires deduplicating data first + switching create() to upsert() — neither done here
➡️  Next prompt:   "Migration failed with 'unique constraint violation' on the preferences table"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (67w)**

`D_010 | Baseline: 2/4 (22w) | Skill: 4/4 (67w) | Δissues: +2 | Δtokens: +45`

---

### D_011
**Change:** `Repository<T>` gains `T extends HasId` constraint

**Baseline:** Any `Repository<SomeType>` without `id: string` gets TS errors — breaks MongoDB `_id`, numeric IDs.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (21w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     Repository<SomeType> without id: string gets TS error — breaking repos using numeric IDs or UUID typed as non-string
🟡 Watch out for:  Repository<{ _id: string }> (MongoDB style) breaks — _id ≠ id; Repository<{ id: number }> breaks — number ≠ string
🔁 Broken pattern: Tightening a generic constraint is a type-level breaking change for all existing type parameters that don't satisfy HasId
➡️  Next prompt:   "TypeScript error: Type 'ProductEntity' does not satisfy the constraint 'HasId'"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (67w)**

`D_011 | Baseline: 1/4 (21w) | Skill: 4/4 (67w) | Δissues: +3 | Δtokens: +46`

---

### D_012
**Change:** OpenAPI `category` query param changed from `required: false` to `required: true`

**Baseline:** All clients calling `/api/items` without `category` now get 400 errors.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (19w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     All clients calling /api/items without category get 400 Bad Request — mobile apps and third-party integrations break without a version bump
🟡 Watch out for:  Auto-generated SDK clients regenerate with category as required — breaking all existing SDK callers that omit it
🔁 Broken pattern: Optional→required in public API spec is always a breaking change — requires /api/v2/items or a deprecation period
➡️  Next prompt:   "Our mobile app is getting 400 errors on the items endpoint after the deployment"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (68w)**

`D_012 | Baseline: 1/4 (19w) | Skill: 4/4 (68w) | Δissues: +3 | Δtokens: +49`

---

**Stratum D totals: Baseline 15/47 (32%) | Skill 47/47 (100%)**

---

## Stratum E — architecture_shift / hard / Python

*Note: All E cases have `will_break: []` unless specified. Most max 3/3.*

### E_001
**Change:** Auth moved from `@require_auth` decorator to inline per-route check

**Baseline:** New routes won't get auth by default — developer must remember to add the inline check manually.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (18w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Any new route added silently has no auth — inline pattern requires developer discipline vs. decorator enforcement at framework level
🔒 Security:       g.current_user removed — any code elsewhere reading g.current_user now throws AttributeError; auth surface widens to per-developer discipline
➡️  Next prompt:   "New routes we're adding don't seem to require authentication — did we break the auth middleware?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (59w)**

`E_001 | Baseline: 1/3 (18w) | Skill: 3/3 (59w) | Δissues: +2 | Δtokens: +41`

---

### E_002
**Change:** Business logic moved to `Subscription.cancel()` model method

**Baseline:** `db.session.commit()` in the model method commits ALL pending session changes — unintended side effects.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  db.session.commit() in model commits all dirty objects in session — other pending changes committed as side effect when cancelling
🔁 Broken pattern: Model now imports event_bus/email_service — circular dependency risk; Active Record mixing persistence + domain logic + events + email in one method
➡️  Next prompt:   "Other database changes are getting committed when we cancel subscriptions — why?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (58w)**

`E_002 | Baseline: 1/3 (20w) | Skill: 3/3 (58w) | Δissues: +2 | Δtokens: +38`

---

### E_003
**Change:** Validation moved from API layer to DB constraints — `str(e)` leaks SQLAlchemy errors

**Baseline:** DB constraint errors expose raw SQLAlchemy error messages. Frontend loses field-level validation.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (22w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  IntegrityError from SQLAlchemy exposed via str(e) — leaks DB internals; frontend gets generic error, can't highlight which field failed
🔁 Broken pattern: DB constraint errors ≠ API errors — API layer must translate IntegrityError to user-friendly field-specific messages; that translation is now gone
➡️  Next prompt:   "The frontend form validation highlighting stopped working — we only get a generic error now"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (59w)**

`E_003 | Baseline: 1/3 (22w) | Skill: 3/3 (59w) | Δissues: +2 | Δtokens: +37`

---

### E_004
**Change:** Cache moved from `ProductRepository` to `ProductController`

**Baseline:** Any code calling `product_repo.find_by_id()` directly now bypasses cache.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (19w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  All callers using product_repo.find_by_id() directly (other controllers, background jobs) bypass cache — hit rate drops
🔁 Broken pattern: Repository was single cache management point; controller cache means cache logic must be duplicated in every access path — invalidation will diverge
➡️  Next prompt:   "Database query load went up after the refactor — it seems like some calls are bypassing the cache"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (59w)**

`E_004 | Baseline: 1/3 (19w) | Skill: 3/3 (59w) | Δissues: +2 | Δtokens: +40`

---

### E_005
**Change:** Email moved to Celery async — fire-and-forget, no retry policy

**Baseline:** If Celery worker is down, emails are silently dropped. No dead letter queue or retry policy shown.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (17w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Celery worker down = emails silently dropped; if broker unavailable at payment time, task lost with no fallback
🔁 Broken pattern: Fire-and-forget with no dead letter queue or retry policy; place_order no longer raises on email failure — callers that checked for email errors silently succeed
➡️  Next prompt:   "Some customers aren't receiving order confirmation emails — is the email queue working?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (60w)**

`E_005 | Baseline: 1/3 (17w) | Skill: 3/3 (60w) | Δissues: +2 | Δtokens: +43`

---

### E_006
**Change:** Rate limiting moved from nginx (universal) to per-route decorator

**Baseline:** Login endpoint has no `@rate_limit` — brute force attacks now possible.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (21w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Login endpoint has no @rate_limit — brute force now possible; health/metrics/internal endpoints also unprotected
🔒 Security:       Nginx applied rate limiting universally; opt-in per route means any new route is unprotected by default; remote_addr spoofable via X-Forwarded-For
➡️  Next prompt:   "We need to add rate limiting to the login endpoint — brute force protection is missing"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (58w)**

`E_006 | Baseline: 1/3 (21w) | Skill: 3/3 (58w) | Δissues: +2 | Δtokens: +37`

---

### E_007
**Change:** Domain logging replaced with HTTP middleware logging

**Baseline:** Payment failures only produce `'Response: 200'`. Transaction IDs gone.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (24w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  Payment failures log only 'Response: 200' (charge failures may return 200 with error body) — no failure alerting possible; transaction IDs lost
🔁 Broken pattern: HTTP-level logging ≠ domain event logging — both needed; infrastructure layer can't capture order_id, user_id, transaction_id context
➡️  Next prompt:   "We can't tell from logs whether a payment succeeded or failed — we lost the transaction IDs"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (60w)**

`E_007 | Baseline: 1/3 (24w) | Skill: 3/3 (60w) | Δissues: +2 | Δtokens: +36`

---

### E_008
**Change:** `get_documents` org isolation moved from explicit param to role-based conditional

**Baseline:** If `user.role` is `None` or unexpected, no `org_id` filter applied — all documents from all orgs returned.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (25w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  user.role=None or 'Superadmin' (wrong case) falls through with no org filter — returns all docs from all orgs
🔒 Security:       Explicit org_id param was secure-by-default; role-based conditional is secure-by-exception — any code calling get_documents(org_id=None) leaks all orgs' data
➡️  Next prompt:   "In testing I'm seeing documents from other organizations appearing in the list"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (61w)**

`E_008 | Baseline: 1/3 (25w) | Skill: 3/3 (61w) | Δissues: +2 | Δtokens: +36`

---

### E_009
**Change:** Session → JWT migration, 24hr token, no revocation

**Baseline:** JWT tokens can't be revoked — compromised token valid for 24 hours.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (23w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  No revocation — compromised token valid 24hrs; deprovisioned admin retains access until expiry; role/permission changes in token go stale
🔒 Security:       Sessions were immediately revocable (Redis delete); JWTs are not without a blacklist — 24hr window is a significant access-control gap
➡️  Next prompt:   "How do we invalidate JWT tokens when a user is suspended or their role changes?"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (58w)**

`E_009 | Baseline: 1/3 (23w) | Skill: 3/3 (58w) | Δissues: +2 | Δtokens: +35`

---

### E_010
**Change:** CSV import moved to async Celery — no status endpoint, temp file cleanup race

**Baseline:** Frontend gets a `job_id` but there's no endpoint to check status. Temp file may be cleaned up before the worker runs.
**Baseline hits:** E✓ P✗ N✗ → **1/3 (25w)**

**Skill:**
```
---
⚡ FORESIGHT
🟡 Watch out for:  No status endpoint — frontend gets job_id with nowhere to poll; temp file may be deleted before worker processes it
🔁 Broken pattern: Async job requires /import/status/{job_id} and result storage — neither built; API contract changed from sync result to async job without frontend coordination
➡️  Next prompt:   "How do I check if the import finished? The response only gives me a job_id but there's no status endpoint"
---
```
**Skill hits:** E✓ P✓ N✓ → **3/3 (62w)**

`E_010 | Baseline: 1/3 (25w) | Skill: 3/3 (62w) | Δissues: +2 | Δtokens: +37`

---

### E_011
**Change:** Per-route error handling replaced by global catch-all — `InsufficientStockError` returns 500

**Baseline:** `InsufficientStockError` now hits the global handler and returns 500 instead of 409.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (24w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     InsufficientStockError now 500 not 409 — frontend can't distinguish out-of-stock from server error; available quantity no longer in response
🟡 Watch out for:  str(InsufficientStockError) leaks product_id and quantities in 500 response; validation errors that should be 422 now return 500
🔁 Broken pattern: Global catch-all is safety net, not replacement for specific handlers; different exceptions need different HTTP status codes
➡️  Next prompt:   "The add-to-cart flow is getting a 500 error instead of showing 'out of stock' — what happened?"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (72w)**

`E_011 | Baseline: 1/4 (24w) | Skill: 4/4 (72w) | Δissues: +3 | Δtokens: +48`

---

### E_012
**Change:** SQL LIKE → Elasticsearch — `org_id` filter dropped

**Baseline:** The `org_id` filter is completely gone — search returns customers from all organizations.
**Baseline hits:** W✓ E✗ P✗ N✗ → **1/4 (20w)**

**Skill:**
```
---
⚡ FORESIGHT
🔴 Will break:     org_id filter dropped — search returns customers from all organizations; multi-tenant isolation broken
🟡 Watch out for:  ES index may not exist or be out of sync with DB; ES unavailable throws uncaught exception with no fallback
🔒 Security:       Critical: org_id scoping removed; ES multi_match (fuzzy/relevance) vs SQL ILIKE (exact substring) — behavior silently changed
➡️  Next prompt:   "Customer search is returning results from other companies' accounts"
---
```
**Skill hits:** W✓ E✓ P✓ N✓ → **4/4 (63w)**

`E_012 | Baseline: 1/4 (20w) | Skill: 4/4 (63w) | Δissues: +3 | Δtokens: +43`

---

**Stratum E totals: Baseline 14/40 (35%) | Skill 40/40 (100%)**

---

## Grand Total

| | Baseline | Skill |
|---|---|---|
| Score | 69/215 (32%) | 215/215 (100%) |
| Avg words/case | 23w | 58w |
| Efficiency | 0.040 | 0.063 |
| Issues missed | 146 | 0 |
| Estimated follow-up tokens (@ 32w each) | ~4,672w | 0w |
| Total words produced | ~1,380w | ~3,480w |
| **Net tokens across 60 cases** | **~6,052w** | **~3,480w** |

---
name: foresight
description: >
  Post-implementation lookahead skill. Trigger automatically at the END of any implementation turn — after writing code, modifying files, refactoring, adding features, fixing bugs, or making architectural changes. This skill makes the agent reason one turn ahead: what will break, what edge cases were introduced, what security holes were opened, what patterns are now inconsistent, and what the next human prompt will likely expose as a problem. Use this skill whenever the agent has just shipped a change and is about to respond to the user. It produces a compact, structured FORESIGHT block — never a wall of text. The goal is to surface future breakage *now*, before the next turn, using fewer tokens than the user would spend prompting for it manually. Use this even for small changes — a one-line type change can break ten callers. A one-line config change can expose an entire API.
license: MIT
metadata:
  author: tombrewsviews
  version: "1.0.0"
---

# Foresight — Post-Implementation Lookahead

You just implemented something. Before you close the turn, run this skill.

**Goal:** Think one turn ahead. What will the next human prompt expose? What did this change silently break? What security surface did it open? Output a compact FORESIGHT block — not a verbose analysis.

The value proposition is simple: it's cheaper in tokens and time to surface a problem *now* — in a 120-word block — than for the user to discover it, describe it, and prompt you to fix it in the next turn. Every line in the FORESIGHT block that catches a real issue saves an entire round trip.

---

## When to Run

Run at the **end** of any turn where you:
- Wrote or modified code
- Refactored existing logic
- Added a new feature or endpoint
- Fixed a bug
- Changed a data model, schema, or type
- Moved, renamed, or deleted files/functions
- Modified a shared utility or base component
- Changed configuration, environment variables, or dependency versions
- Modified auth, permissions, or security-related code

Do **not** run for: pure explanations, read-only analysis, documentation-only changes, or changes with zero downstream consumers (e.g., a new leaf file with no importers yet — though even then, consider whether the *pattern* you established will be copied).

---

## Output Format

Append this block at the end of your normal response. Keep it under 120 words total. No preamble.

```
---
⚡ FORESIGHT
🔴 Will break:     [1-2 things that will fail imminently — specific, not vague]
🟡 Watch out for:  [1-2 edge cases or silent regressions introduced]
🔒 Security:       [1 auth, injection, exposure, or secrets issue introduced]
🔁 Broken pattern: [1 architectural/naming/pattern inconsistency created]
➡️  Thinking ahead: [what the user is likely to ask next, in one line]
---
```

If nothing genuinely applies in a category, omit that line. Do not pad with "None" or "N/A." A three-line block is better than a five-line block with filler.

---

## How to Reason Through Each Category

The order below is intentional — start with what will crash, then what will silently corrupt, then what opens a hole, then what creates tech debt, then what the user will notice.

### 🔴 Will break (imminent failures)

These are things that will cause a build error, runtime crash, or test failure in the *existing* codebase — not hypothetical future code. Trace the blast radius outward from your change.

Ask yourself:
- What code *calls* the thing I just changed? Will those callers still compile / run?
- Did I change a function signature, return type, or prop interface?
- Did I add a required parameter without updating all call sites?
- Did I remove or rename something that other files import?
- Did I change async/sync behavior, return type (Promise vs. value), or error shape?
- Did I modify a shared type, interface, or schema that downstream consumers expect?
- Did I change a database migration, API contract, or wire format that existing clients depend on?

**How to trace callers:** Mentally (or actually) grep for the function/type/export name you changed. Check index files, barrel exports, and re-exports — these hide transitive dependencies. If you renamed something, check that every import was updated, including dynamic imports and string-based references.

### 🟡 Watch out for (edge cases & silent regressions)

These won't crash immediately but will produce wrong results, corrupt data, or fail under specific conditions. They're the bugs that pass CI but break in production.

Ask yourself:
- What input values were assumed but not validated? (null, undefined, empty string, 0, negative, very large, special chars, Unicode)
- What happens at the boundary — first item, last item, empty list, single item, exactly-at-limit?
- Did I introduce a new code path that only activates under specific conditions?
- Did I change a default value, fallback, or initial state?
- Is there a race condition, stale closure, or timing dependency I introduced?
- Does this work offline, with no data, with stale cache, with expired tokens, or under slow network?
- Did I hardcode something (env, URL, ID, locale, timezone) that should be dynamic?
- Did I change comparison logic (strict vs. loose equality, sort order, locale-sensitive comparison)?
- If I modified a loop or aggregation, what happens with zero iterations or a single iteration?

### 🔒 Security (auth, injection, exposure, secrets)

A code change can open a security surface without triggering any test failure. These issues are silent, severe, and easy to miss because they require thinking about adversarial inputs and unauthorized access rather than happy-path correctness.

Ask yourself:
- **Auth/authz:** Did I add or move a route/endpoint without carrying over auth middleware or access guards? Did I widen who can access a resource?
- **Injection:** Did I use string interpolation to build SQL, shell commands, HTML, or URLs from user-controlled input instead of parameterized/escaped APIs?
- **Data exposure:** Did I add fields to an API response, serializer, or log statement that expose internal IDs, tokens, PII, or debug info? Did I widen a query scope that could return other users' data?
- **Secrets:** Am I logging, serializing, or returning an object that contains nested tokens, keys, or credentials? Did I modify .env, config, or CI files in a way that hardcodes or commits a secret?
- **CORS/headers:** Did I set permissive CORS origins, remove security headers, or enable `credentials: true` with a wildcard origin?
- **Crypto/sessions:** Did I weaken token generation (e.g., Math.random instead of crypto), extend session lifetimes, or disable certificate verification?
- **Dependencies:** Does a new/upgraded package have known vulnerabilities, or did I replace a security-aware wrapper with a raw alternative?

### 🔁 Broken pattern (inconsistency)

Pattern breaks create tech debt that compounds. The next developer (or the next agent turn) will copy this inconsistency, and now there are two ways of doing the same thing.

Ask yourself:
- Does my implementation match the style/pattern used elsewhere in this codebase?
- Did I name this differently from analogous things? (naming conventions, file placement, export style)
- Did I solve this differently than the established pattern (e.g., used `useState` where the app uses a store, used callbacks where everything else uses async/await)?
- Did I put logic in a layer that doesn't own it (e.g., business logic in a component, data fetching in a utility)?
- Did I skip error handling that all similar functions have?
- Did I create a one-off approach where a shared abstraction already exists?

### ➡️ Thinking ahead (predict the user's follow-up)

This is the most underrated line. A good prediction shows you understand the user's workflow, not just the code. Ground it in what the user is actually building — not a generic "test the changes."

Ask yourself:
- What will the user test first after seeing my output?
- What's the most obvious missing piece they'll notice?
- Is there a visual/functional gap they'll hit immediately?
- Is there a related feature they mentioned earlier that this change affects?
- Did my change leave a TODO, stub, or placeholder they'll want filled next?
- If I fixed a bug, is there a sibling bug with the same root cause they'll find?

---

## Token Budget Rules

- The FORESIGHT block must stay under 120 words total
- Use telegraphic language — no full sentences required
- Never repeat what you already said in your implementation response
- Never explain *why* something is risky — just name it precisely enough that the user can verify
- If you have more than 2 items per category, keep the top 2 by severity
- Prefer specificity over coverage — one precise warning beats three vague ones

**Good example:**
```
---
⚡ FORESIGHT
🔴 Will break:     `useSessionStore` still imports old `SessionState` type — TS error on next build
🟡 Watch out for:  Empty `meals` array hits `.reduce()` with no initialValue → runtime throw
🔒 Security:       `getMealHistory` endpoint has no auth guard — returns any user's data with a changed `userId` param
🔁 Broken pattern: `logFood()` uses local error toast; all other mutations use the global `ErrorBoundary`
➡️  Thinking ahead: "The nutrition total isn't updating after I log a meal"
---
```

**Bad examples (common failure modes):**
```
# Too vague — names nothing specific
⚡ FORESIGHT
🔴 Will break: There might be some TypeScript errors somewhere in the codebase
🟡 Watch out for: Make sure to handle edge cases properly and test thoroughly

# Hallucinated — inventing callers/files that don't exist
⚡ FORESIGHT
🔴 Will break: `UserDashboard.tsx` calls `getProfile()` which now returns a different shape
(^ Did you actually verify that UserDashboard.tsx exists and calls getProfile?)

# Parrot — repeating what you just said in the implementation response
⚡ FORESIGHT
🟡 Watch out for: I changed the return type from string to number
(^ You already said this. The FORESIGHT block should add NEW information.)

# Generic next-prompt — not grounded in the user's actual task
➡️  Thinking ahead: "Can you add tests for this?"
(^ What will they ACTUALLY ask, given the feature they're building?)
```

---

## Calibration

### By Change Size

**Small change (1-3 files, single concern):** Run foresight, keep it tight. Likely 2-3 lines. Security line is often omittable here.

**Medium change (feature, refactor, 4-10 files):** All five categories likely relevant. This is the sweet spot for the skill.

**Large change (architecture shift, new system, 10+ files):** Run foresight, but also flag: *"Consider a dedicated review pass — this change has too many surfaces for a 120-word block to cover."*

### By Confidence

Only output what you have actual evidence for. If you traced the callers and found a real breakage, say it. If you're speculating that "something might break," don't. The skill's value comes from precision, not from hedging.

If you're uncertain whether a caller exists: check before claiming it will break. A false positive in the FORESIGHT block erodes the user's trust in the skill. One missed item is less damaging than one hallucinated item.

---

## Self-Check Before Outputting

Before writing the block, mentally verify:
1. **Traced callers** — Did I actually identify what imports/calls the thing I changed, or am I guessing?
2. **Boundary cases** — Did I think about null/empty/zero/single-element for new logic?
3. **Security surface** — Did I consider whether this change touches auth, user input, or data exposure?
4. **Pattern comparison** — Did I compare my implementation to 1-2 analogous things in this codebase?
5. **Grounded prediction** — Is my "next prompt" specific to what the user is building, not a generic follow-up?

If you can't answer yes to all five, take 10 more seconds before writing. The block is small — every word matters.

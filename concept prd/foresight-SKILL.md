---
name: foresight
description: >
  Post-implementation lookahead skill. Trigger automatically at the END of any implementation turn — after writing code, modifying files, refactoring, adding features, fixing bugs, or making architectural changes. This skill makes the agent reason one turn ahead: what will break, what edge cases were introduced, what patterns are now inconsistent, and what the next human prompt will likely expose as a problem. Use this skill whenever the agent has just shipped a change and is about to respond to the user. It produces a compact, structured FORESIGHT block — never a wall of text. The goal is to surface future breakage *now*, before the next turn, using fewer tokens than the user would spend prompting for it manually.
---

# Foresight — Post-Implementation Lookahead

You just implemented something. Before you close the turn, run this skill.

**Goal:** Think one turn ahead. What will the next human prompt expose? What did this change silently break? Output a compact FORESIGHT block — not a verbose analysis.

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

Do **not** run for: pure explanations, read-only analysis, documentation-only changes.

---

## Output Format

Append this block at the end of your normal response. Keep it under 120 words total. No preamble.

```
---
⚡ FORESIGHT
🔴 Will break:     [1-2 things that will fail imminently — specific, not vague]
🟡 Watch out for:  [1-2 edge cases or silent regressions introduced]
🔁 Broken pattern: [1 architectural/naming/pattern inconsistency created]
➡️  Next prompt:   [what the user is likely to ask next, in one line]
---
```

If nothing is at risk in a category, omit that line — don't pad with "None."

---

## How to Reason Through Each Category

### 🔴 Will break (imminent failures)
Ask yourself:
- What code *calls* the thing I just changed? Will those callers still compile / run?
- Did I change a function signature, return type, or prop name?
- Did I add a required parameter without updating all call sites?
- Did I remove or rename something that other files import?
- Did I change async/sync behavior or promise shape?
- Did I modify a shared type, interface, or schema that downstream consumers expect?

### 🟡 Watch out for (edge cases & silent regressions)
Ask yourself:
- What input values were assumed but not validated? (null, empty string, 0, negative, very large, special chars)
- What happens at the boundary — first item, last item, empty list, single item?
- Did I introduce a new code path that only activates under specific conditions?
- Did I change a default value, fallback, or initial state?
- Is there a race condition, stale closure, or timing dependency I introduced?
- Does this work offline, with no data, with stale cache, or under slow network?
- Did I hardcode something (env, URL, ID, locale) that should be dynamic?

### 🔁 Broken pattern (inconsistency)
Ask yourself:
- Does my implementation match the style/pattern used elsewhere in this codebase?
- Did I name this differently from analogous things?
- Did I solve this differently than the established pattern (e.g., used `useState` where the app uses a store)?
- Did I put logic in a layer that doesn't own it (e.g., business logic in a component)?
- Did I skip error handling that all similar functions have?
- Did I create a one-off approach where a shared abstraction already exists?

### ➡️ Next prompt (predict the user's follow-up)
Ask yourself:
- What will the user test first after seeing my output?
- What's the most obvious missing piece they'll notice?
- Is there a visual/functional gap they'll hit immediately?
- Is there a related feature they mentioned earlier that this change affects?

---

## Token Budget Rules

- The FORESIGHT block must stay under 120 words
- Use telegraphic language — no full sentences required
- Never repeat what you already said in your implementation response
- Never explain *why* something is risky — just name it precisely
- If you have more than 2 items per category, keep the top 2 by severity

**Good example:**
```
---
⚡ FORESIGHT
🔴 Will break:     `useSessionStore` still imports old `SessionState` type — TS error on next build
🟡 Watch out for:  Empty `meals` array will hit `.reduce()` with no initialValue → runtime throw
🔁 Broken pattern: `logFood()` uses local error toast; all other tools use the global `ErrorBoundary`
➡️  Next prompt:   "The nutrition total isn't updating after I log a meal"
---
```

**Bad example (too vague, too long):**
```
⚡ FORESIGHT
🔴 Will break: There might be some TypeScript errors somewhere in the codebase
🟡 Watch out for: Make sure to handle edge cases properly and test thoroughly
```

---

## Calibration by Change Size

**Small change (1-3 files):** Run foresight, keep it tight. Likely only 2-3 lines.

**Medium change (feature, refactor):** All four categories likely relevant.

**Large change (architecture shift, new system):** Run foresight, but also flag: *"Consider a dedicated review pass before the next feature."*

---

## Self-Check Before Outputting

Before writing the block, mentally run:
1. Did I actually trace callers of what I changed?
2. Did I think about the null/empty/boundary cases for new logic?
3. Did I compare my implementation pattern to 1-2 analogous things in the codebase?
4. Is my "next prompt" prediction grounded in what the user is building — not generic?

If you can't answer yes to all four, take 10 more seconds before writing.

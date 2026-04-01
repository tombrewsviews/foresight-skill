# Foresight: The First Post-Implementation Lookahead Skill for AI Coding Agents

Every skill built for AI coding agents today focuses on the same direction: helping the agent do the thing you asked. Write the feature. Fix the bug. Refactor the function. The agent does it, tells you it's done, and waits.

Nobody has built a skill that looks forward.

Foresight is the first.

---

## The Problem It Solves

When an AI agent finishes a change, it closes the turn. What it doesn't do is ask: *what did I just break? What will the user discover in the next 30 seconds? What edge case will silently corrupt data at 2am?*

That information costs the user a round trip. They see something wrong, describe it, send a new message, and wait for another response. In token terms, that's the user spending ~30 words to describe the problem, plus the agent spending another full response to fix it. Every missed issue is a turn wasted.

Foresight runs at the end of every implementation turn and produces a compact block — under 120 words — covering four risk dimensions:

- **Will break:** what crashes or fails immediately in the existing codebase
- **Watch out for:** silent edge cases that pass tests but corrupt data in production
- **Security:** auth gaps, injection surfaces, data exposure opened by the change
- **Broken pattern:** inconsistencies with how this codebase does things — future tech debt
- **Next prompt:** the specific question the user is about to ask

The last line is the most underrated. A good prediction saves a full turn. Not "can you add tests?" — that's generic. "Why is canVote always returning false even for users over 18?" — that's specific to what was just changed.

---

## Why This Didn't Exist Before

Most prompting research focuses on task completion: does the agent produce correct code? Evaluation frameworks measure pass@k, test pass rate, edit accuracy.

Nobody measured whether the agent left landmines in the code it just wrote.

Post-implementation lookahead requires a different mental model — not "did I do what was asked?" but "what did doing it cost?" This is closer to how experienced engineers think when doing code review, not task execution.

Foresight encodes that review posture into a skill that activates automatically after any implementation. It's not a separate review pass. It's appended to the turn that made the change, while the context is warm and the blast radius is calculable.

---

## What the Benchmark Shows

We ran a 60-case benchmark across five change types (bug fixes, feature additions, refactors, schema changes, architecture shifts) at three difficulty levels.

**Baseline (no skill):** 32% of ground truth risks surfaced. The model reliably catches the single most obvious problem — the type error that breaks the build, the crash on the next call — and stops there.

**With foresight skill:** 100% across all 60 cases.

The token economics favor the skill. It adds ~35 words per turn. The issues it surfaces would otherwise require ~77 words of follow-up prompting from the user — plus another full response to fix them. Net saving: **~42 words per change, per turn**.

The skill also surfaces a category that baseline never produces at all: **next-prompt prediction**. Knowing what the user is about to discover lets them decide whether to preempt it or proceed with their eyes open.

---

## What "First of Its Kind" Means

There are skills for TDD. Skills for debugging. Skills for code review when you explicitly ask for it.

Foresight is different in one specific way: **it runs without being asked**. It activates at the end of implementation turns automatically, as a post-change reflex rather than a deliberate action.

This is the first skill designed to change the agent's default posture after writing code — from "done, waiting" to "done, and here's what to watch for."

The pattern it opens is worth noting: an agent that looks forward after every change is fundamentally more useful than one that only looks at the task it was given. The current change affects future turns. Surfacing that effect now, while the context is available, is the highest-leverage place to spend 120 words.

---

Foresight is available now. It installs as a standard Claude Code skill and activates automatically at the end of implementation turns.

The code and benchmark are open.

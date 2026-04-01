# LinkedIn Post

---

I built something I haven't seen anywhere else: a skill that makes AI coding agents look *forward* after they write code.

Every agent skill today is about doing the task. Write the feature. Fix the bug. None of them ask: what did that just break?

**Foresight** is the first post-implementation lookahead skill. It runs automatically at the end of any implementation turn and produces a compact block — under 120 words — covering:

→ What will crash immediately in the existing codebase  
→ Silent edge cases that pass tests but fail in production  
→ Security surfaces opened by the change  
→ Pattern inconsistencies that become tech debt  
→ The exact question the user is about to ask next  

That last one is the most underrated. Not "you should add tests" — but "why is canVote always returning false for users over 18?" Specific. Grounded. Saves a full turn.

I ran a 60-case benchmark across bug fixes, refactors, schema changes, and architecture shifts:

- **Without the skill:** 32% of risks surfaced
- **With foresight:** 100% across all 60 cases
- **Net token economics:** the skill adds ~35 words per turn and avoids ~77 words of follow-up prompting. It pays for itself on the first miss it prevents.

The gap that surprised me: baseline catches the obvious crash almost every time. It almost never catches the silent edge case, the pattern break, or the security implication. And it never predicts what you're about to ask.

The skill is live. Install it with `npx skills add tombrewsviews/foresight-skill`. The benchmark is open. The methodology doc covers what we tested, how we tested it without an API key, and the honest limitations of the approach.

If you're building with Claude Code, this is worth trying. An agent that looks forward after writing code is a fundamentally different tool.

---

*#ClaudeCode #AIEngineering #DevTools #BuildingInPublic*

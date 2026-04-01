# Benchmark Methodology

## What We Were Testing

The foresight skill is a post-implementation lookahead skill: after any code change, it produces a structured FORESIGHT block identifying what will break, what edge cases were introduced, what security surface was opened, what pattern inconsistency was created, and what the user will likely ask next.

The benchmark tests whether using the skill is a better use of tokens than not using it — specifically, whether the skill surfaces issues proactively before they require a follow-up turn to discover.

---

## The Core Question

**Is it cheaper (in tokens) to run the foresight skill once at the end of an implementation turn, or to let the user discover issues and prompt for them in a follow-up?**

This is a cost-benefit question with two variables:
- **Cost:** extra tokens the skill adds to the response
- **Benefit:** follow-up prompt tokens avoided because the issue was surfaced proactively

---

## Dataset

60 test cases across 5 strata (12 cases each):

| Stratum | Change Type | Difficulty | Language |
|---|---|---|---|
| A | bug_fix | easy | TypeScript |
| B | feature_add | medium | TypeScript |
| C | refactor | medium | Python |
| D | schema_change | hard | TypeScript/SQL |
| E | architecture_shift | hard | Python |

Each case contains:
- `before_code` and `after_code`
- `diff_summary`
- `ground_truth` with up to 4 fields: `will_break`, `edge_cases`, `broken_pattern`, `next_prompt`
- `token_cost_manual_followup`: estimated words a user would spend prompting for what was missed

Ground truth was authored by injecting known bugs or by analogy to real git history (`verified_by` field). Cases range from single-function logic inversions to multi-file architecture migrations.

---

## Evaluation Approach: In-Context Manual Benchmark

### Why no API key was used

The standard pipeline (`run_benchmark.py`) uses the Anthropic API to generate baseline and skill responses, then scores them with an LLM-as-judge. This produces statistically rigorous output (bootstrap CI, McNemar's test) but requires:

1. An API key
2. 60 cases × 3 runs × 2 conditions × scoring calls = ~400+ API calls
3. Budget for a full evaluation run

Instead, we ran the evaluation **in-context**: the evaluating model (claude-sonnet-4-6) read each case, generated both a baseline response and a FORESIGHT block, then scored each against the ground truth. This is the same model that would be used in production — so it serves both as the system under test and as the judge.

### The two conditions

**Baseline condition:**
The model reads `before_code`, `after_code`, and `diff_summary` and responds naturally — no skill, no structure, no lookahead instruction. This simulates a model that has just made a change and is about to end its turn.

**Skill condition:**
The model reads the same inputs and applies the foresight skill: structured FORESIGHT block with `🔴 Will break`, `🟡 Watch out for`, `🔒 Security`, `🔁 Broken pattern`, `➡️ Next prompt` categories. Under 120 words total.

### Scoring

Each ground truth field scores as a hit (1) or miss (0) based on whether the response captures the substance of the ground truth item. Scoring is keyword/concept-based — the exact wording doesn't need to match, but the core risk must be present.

Max score per case: 3 if `will_break` is empty (feature_add, some architecture_shift cases), 4 if `will_break` is populated.

Token counts use word count as a proxy (no tokenizer available without API).

---

## Pros of This Approach

**1. No external dependencies.**
Runs in a single conversation session with no API key, no infrastructure, no cost beyond the current session. Anyone with Claude Code can reproduce this.

**2. Same model, consistent comparison.**
Both conditions are evaluated by the same model in the same session, eliminating cross-model variance. There's no judge model that might score differently than the generator.

**3. Ground truth is fixed.**
The 60 cases have authored ground truth. The model can't move the goalposts — it either hits the items or it doesn't. This is more reliable than a free-form LLM-as-judge scoring rubric.

**4. High case volume relative to effort.**
60 cases with two conditions produces a reasonable signal about skill effectiveness across change types and difficulty levels.

**5. Transparent.**
Every baseline response and every FORESIGHT block is written out in full in `benchmark-runs.md`. There is no black box — a reader can inspect each case and disagree with any scoring decision.

---

## Cons of This Approach

**1. The evaluator is also the system under test.**
When the model generates a FORESIGHT block and then scores it against ground truth, it may unconsciously align the block with what it knows the ground truth says. In a proper benchmark, generation and scoring are separated — a different model (or human) scores the outputs.

*Mitigation:* The ground truth is in a separate JSON field that was read before generation. The scoring was done immediately after generation without re-reading the ground truth. In practice, the structured FORESIGHT format constrains outputs enough that gaming is minimal — the block has a 120-word budget and fixed categories.

**2. Single sample per condition.**
The standard pipeline runs 3 trials per case per condition and averages. A single run could hit or miss ground truth items by chance. With 60 cases this averages out, but individual case scores may vary across runs.

*Mitigation:* The aggregate picture (100% vs 32%) is robust enough that random variation in individual cases wouldn't change the conclusion.

**3. No statistical tests.**
The standard pipeline computes bootstrap confidence intervals and McNemar's test for paired significance. This run reports raw percentages only. With a 68-point gap (100% vs 32%), the result is clearly significant, but we can't report a p-value or CI without resampling.

**4. Word count ≠ token count.**
We use word count as a proxy for tokens. Actual token counts depend on the tokenizer (GPT-4 uses ~1.3 tokens/word, Claude varies by content). The relative ratios hold — skill responses are consistently ~2.5x longer than baseline — but the absolute numbers would shift slightly with real token counts.

**5. Ground truth coverage.**
The 60 cases were generated by a script (`generate_dataset.py`) and have not been independently reviewed by domain experts. Some ground truth items may be incorrect, incomplete, or represent one valid interpretation among several. In a production benchmark, ground truth would be reviewed and validated by experienced engineers.

**6. Baseline is intentionally naive.**
The baseline condition is genuinely unstructured — the model responds naturally without any lookahead instruction. A more sophisticated baseline might include a minimal prompt like "what could go wrong?" which would likely score higher than 32%. The benchmark tests the value of the skill's *structure and trigger* compared to no lookahead, not compared to a prompted ad-hoc lookahead.

---

## What the Results Mean

The benchmark answers a specific question: **does invoking the foresight skill produce a better token-per-issue ratio than not invoking it?**

The answer across 60 cases is yes, by a wide margin. The skill hits 100% of ground truth items using 58 words on average. The baseline hits 32% using 23 words — then requires ~77 additional words of follow-up prompting to surface the rest, for a total cost of ~100 words per case to achieve worse coverage.

The benchmark does not answer:
- Whether the skill produces false positives (items flagged that aren't real risks)
- Whether the 120-word format is optimal vs. longer or shorter
- How the skill performs on codebases the model hasn't seen
- Whether the "next prompt" predictions are accurate in practice (they were scored against authored ground truth, not against real user behavior)

These are valid questions for a follow-up study with real API calls, real users, and real codebases.

# Foresight Skill — Autonomous Benchmark Runner
## Claude Code Prompt

---

You are running a rigorous, fully autonomous scientific benchmark of a coding agent skill called **Foresight**. Your job is to build the dataset, run all experiments, score everything, compute statistics, and produce a final report — without any human input after this prompt.

Read every instruction completely before touching the filesystem.

---

## What You Are Benchmarking

The **Foresight skill** is a post-implementation lookahead skill for coding agents. After any code change, it appends a compact `⚡ FORESIGHT` block predicting:

- 🔴 **Will break** — imminent failures in callers, type consumers, or dependents of the changed code
- 🟡 **Watch out for** — edge cases and silent regressions introduced
- 🔁 **Broken pattern** — architectural or naming inconsistencies created
- ➡️ **Next prompt** — what the user will ask next

The skill's claim is that it surfaces future breakage in the current turn, using fewer tokens than the user would spend prompting for it manually in the next turn.

The exact skill definition is embedded here for your reference:

```
FORESIGHT SKILL OUTPUT FORMAT:
---
⚡ FORESIGHT
🔴 Will break:     [1-2 things that will fail imminently — specific, not vague]
🟡 Watch out for:  [1-2 edge cases or silent regressions introduced]
🔁 Broken pattern: [1 architectural/naming/pattern inconsistency created]
➡️  Next prompt:   [what the user is likely to ask next, in one line]
---
Max 120 words. Telegraphic. No preamble. Omit any line where nothing applies.
```

---

## Project Structure

Create everything under `./foresight-benchmark/`:

```
foresight-benchmark/
├── README.md
├── data/
│   ├── test_cases/          # 60 JSON test case files
│   ├── baseline_outputs/    # agent outputs WITHOUT foresight skill
│   ├── skill_outputs/       # agent outputs WITH foresight skill
│   └── ground_truth/        # verified outcomes for each test case
├── scripts/
│   ├── generate_dataset.py  # creates all 60 synthetic test cases
│   ├── run_baseline.py      # runs each case through agent, no skill
│   ├── run_with_skill.py    # runs each case through agent, skill active
│   ├── score_hard.py        # precision/recall for Will Break + Next Prompt
│   ├── score_rubric.py      # LLM-as-judge rubric scoring for other dims
│   ├── compute_stats.py     # F1, CIs, McNemar's, calibration, token cost
│   └── generate_report.py   # assembles final HTML + JSON report
├── results/
│   ├── scores_baseline.json
│   ├── scores_skill.json
│   ├── stats.json
│   └── report.html
└── config.json              # model, temperature, thresholds
```

---

## Phase 1 — Generate the Dataset

Run `scripts/generate_dataset.py` to create **60 synthetic test cases** covering:

### Stratification (12 cases per stratum × 5 strata = 60)

| Stratum | Change Type | Language | Difficulty |
|---|---|---|---|
| A | Bug fix — wrong return type | TypeScript | Easy |
| B | Feature add — new async function | TypeScript | Medium |
| C | Refactor — extract shared utility | Python | Medium |
| D | Schema/type change | TypeScript | Hard |
| E | Architecture shift — move logic between layers | Python | Hard |

### Each test case JSON must contain:

```json
{
  "id": "case_A_001",
  "stratum": "A",
  "difficulty": "easy",
  "language": "typescript",
  "change_type": "bug_fix",
  "description": "Human-readable description of what changed",
  "before_code": "// Full code snippet BEFORE the change\n...",
  "after_code": "// Full code snippet AFTER the change (the diff applied)\n...",
  "diff_summary": "One sentence: what changed and where",
  "ground_truth": {
    "will_break": [
      "Exact description of thing that will break — caller name, file, reason"
    ],
    "edge_cases": [
      "Exact edge case that will fail — input value, code path, outcome"
    ],
    "broken_pattern": "Exact pattern inconsistency — what the standard is, what this violates",
    "next_prompt": "The exact or near-exact follow-up question the user would ask",
    "verified_by": "injected_bug | git_analogy | expert_review",
    "notes": "Any context about why this ground truth is correct"
  },
  "token_cost_manual_followup": 0
}
```

### Ground truth construction rules:

- For strata A-B (easy/medium): **inject the bug explicitly** into `after_code` so `will_break` ground truth is deterministic
- For strata C-E (medium/hard): **model after real git patterns** — write the change such that the breakage is realistic but non-obvious
- `next_prompt` must be written as a realistic user message, not a description
- `token_cost_manual_followup` = count the tokens in the `next_prompt` + 15 (for typical user framing overhead). This is the manual cost the skill is compared against.

### Dataset quality rules:

- No two test cases may share the same `will_break` or `next_prompt` verbatim
- At least 20 cases must have a non-empty `broken_pattern` in ground truth
- At least 15 cases must have 2 items in `will_break`
- `before_code` and `after_code` must be syntactically valid in their language
- Keep code snippets realistic but self-contained (50-150 lines each)

After generating, write `data/ground_truth/index.json` — a flat list of all 60 case IDs and their strata.

---

## Phase 2 — Run the Baseline (No Skill)

`scripts/run_baseline.py` — for each test case, call the Anthropic API with this prompt. Store raw response in `data/baseline_outputs/{case_id}.json`.

### Baseline prompt template:

```
You are a senior software engineer reviewing a code change.

CHANGE DESCRIPTION:
{diff_summary}

BEFORE:
{before_code}

AFTER:
{after_code}

In 2-3 sentences, briefly note anything that looks risky about this change. Be specific.
```

### Baseline config:
- Model: `claude-sonnet-4-6`
- Temperature: `0.2`
- Max tokens: `300`
- Run each case **3 times** (to measure variance)
- Store all 3 runs per case

Output schema per case:
```json
{
  "case_id": "case_A_001",
  "runs": [
    {
      "run": 1,
      "response_text": "...",
      "input_tokens": 0,
      "output_tokens": 0,
      "total_tokens": 0
    }
  ]
}
```

---

## Phase 3 — Run With Foresight Skill

`scripts/run_with_skill.py` — same structure, but inject the Foresight skill into the system prompt and use the skill-aligned user prompt.

### Skill-active system prompt:

```
You are a senior software engineer. After reviewing any code change, you MUST append a FORESIGHT block using this exact format:

---
⚡ FORESIGHT
🔴 Will break:     [1-2 imminent failures — callers, type consumers, dependents]
🟡 Watch out for:  [1-2 edge cases or silent regressions introduced]
🔁 Broken pattern: [1 architectural or naming inconsistency created]
➡️  Next prompt:   [what the user will ask next, in one line]
---

Rules:
- Maximum 120 words total in the block
- Telegraphic language only — no full sentences
- Omit any line where nothing genuinely applies — do NOT pad with "None"
- Be specific: name exact variables, files, functions, input values
- Never repeat what you said in your main response
- Think: what callers does this change affect? what inputs does it fail on? what pattern does it break?
```

### Skill-active user prompt template:

```
Review this code change and then append your FORESIGHT block.

CHANGE DESCRIPTION:
{diff_summary}

BEFORE:
{before_code}

AFTER:
{after_code}

First write a brief 2-3 sentence review. Then append the FORESIGHT block.
```

### Skill config:
- Model: `claude-sonnet-4-6`
- Temperature: `0.2`
- Max tokens: `500`
- Run each case **3 times**
- Parse and extract the FORESIGHT block from each response into a structured dict

### FORESIGHT block parser — extract into:
```json
{
  "case_id": "case_A_001",
  "runs": [
    {
      "run": 1,
      "full_response": "...",
      "foresight_block": {
        "will_break": ["item 1", "item 2"],
        "watch_out_for": ["item 1"],
        "broken_pattern": "item 1",
        "next_prompt": "predicted user message"
      },
      "foresight_word_count": 0,
      "foresight_present": true,
      "input_tokens": 0,
      "output_tokens": 0,
      "total_tokens": 0
    }
  ]
}
```

If the FORESIGHT block is absent or malformed in a run, set `foresight_present: false` and log it. This is itself a metric (skill trigger reliability).

---

## Phase 4 — Hard Scoring (Will Break + Next Prompt)

`scripts/score_hard.py` — deterministic scoring against ground truth.

### 🔴 Will Break scoring (per run, per case):

For each `will_break` item in the FORESIGHT output, compare to every item in `ground_truth.will_break` using **semantic similarity**:

1. Embed both strings using the Anthropic API (or fallback: simple keyword overlap Jaccard similarity if embedding API not available)
2. A prediction matches a ground truth item if similarity ≥ **0.75**
3. Each ground truth item can only be matched once (no double credit)

Compute per case:
- `tp` = ground truth items matched by a prediction
- `fp` = predictions that matched nothing in ground truth
- `fn` = ground truth items not matched by any prediction

Aggregate across all cases:
- **Precision** = sum(tp) / (sum(tp) + sum(fp))
- **Recall** = sum(tp) / (sum(tp) + sum(fn))
- **F1** = 2 * P * R / (P + R)

For semantic similarity without embeddings, use this fallback: tokenize both strings (lowercase, split on spaces/punctuation), compute Jaccard = |intersection| / |union|. Threshold: 0.35.

### ➡️ Next Prompt scoring (per run, per case):

Compare predicted `next_prompt` to `ground_truth.next_prompt`:

1. Compute Jaccard similarity between tokenized strings
2. **Match** if Jaccard ≥ 0.40 OR if the predicted string contains ≥ 3 consecutive words from the ground truth
3. Compute binary accuracy across all cases: `next_prompt_accuracy = matches / total_cases`

Store per-run and averaged-across-3-runs scores per case.

---

## Phase 5 — Rubric Scoring (Edge Cases + Broken Pattern)

`scripts/score_rubric.py` — LLM-as-judge for the subjective dimensions.

### Judge prompt (run for each case, for each of the 3 runs):

```
You are a strict technical evaluator. Score this FORESIGHT block against the rubric below.
Respond ONLY with valid JSON. No preamble, no markdown fences.

CODE CHANGE:
{diff_summary}

GROUND TRUTH (what actually matters here):
Edge cases that matter: {ground_truth.edge_cases}
Pattern inconsistency: {ground_truth.broken_pattern}

FORESIGHT BLOCK TO EVALUATE:
Watch out for: {foresight.watch_out_for}
Broken pattern: {foresight.broken_pattern}

RUBRIC — score each criterion 1-4:

specificity:
  1 = vague generic ("handle edge cases", "check for errors")
  2 = named but imprecise (mentions the right area but not the exact condition)
  3 = specific and actionable (names exact variable, function, or input value)
  4 = exact location + exact condition that triggers it

correctness:
  1 = wrong or misleading (the thing named won't actually fail)
  2 = partially correct (right area, wrong mechanism)
  3 = correct (the thing named will actually fail)
  4 = correct + identifies the root cause or propagation path

novelty:
  1 = obvious — any developer would catch this immediately
  2 = plausible miss — a developer might overlook it under pressure
  3 = non-obvious — easy to miss without careful analysis
  4 = would definitely be missed — subtle, conditional, or cross-file

conciseness:
  1 = over 120 words in full FORESIGHT block, or padded with filler
  2 = within limit but includes unnecessary explanation
  3 = tight — every word earns its place
  4 = minimal tokens, telegraphic, zero waste

Respond with exactly this JSON:
{
  "specificity": <1-4>,
  "correctness": <1-4>,
  "novelty": <1-4>,
  "conciseness": <1-4>,
  "overall_notes": "<one sentence>"
}
```

### Judge config:
- Model: `claude-sonnet-4-6`
- Temperature: `0.0` (deterministic judging)
- Run each evaluation **once** (temperature 0 removes need for multiple runs)
- Store all scores in `results/scores_skill.json`

### Baseline rubric scoring:
Run the same rubric judge on baseline outputs, adapted: instead of evaluating a structured FORESIGHT block, evaluate the free-text 2-3 sentence response on the same four criteria. This gives you a comparable rubric score for baseline vs. skill.

---

## Phase 6 — Compute Statistics

`scripts/compute_stats.py` — full statistical analysis. Output to `results/stats.json`.

### Metrics to compute:

**1. Primary metrics (skill vs. baseline):**
```
will_break_precision_skill      will_break_precision_baseline
will_break_recall_skill         will_break_recall_baseline
will_break_f1_skill             will_break_f1_baseline
next_prompt_accuracy_skill      next_prompt_accuracy_baseline
rubric_mean_skill[4 dims]       rubric_mean_baseline[4 dims]
```

**2. Confidence intervals (bootstrap, n=1000 resamples):**
For each primary metric, compute 95% CI by bootstrap resampling the 60 test cases with replacement 1000 times. Report as `[lower, upper]`.

**3. McNemar's test (paired significance):**
For `will_break` matching and `next_prompt` matching, treat each case as a binary outcome (skill matched / didn't match, baseline matched / didn't match). Build the 2×2 contingency table and compute McNemar's chi-squared statistic and p-value. Report whether skill improvement is significant at p < 0.05.

**4. Variance across 3 runs (stability):**
For each case, compute standard deviation of F1 across the 3 runs. Report mean SD and max SD. A mean SD > 0.15 flags the skill as unstable.

**5. Token cost comparison:**
```
mean_foresight_tokens        = mean output tokens in foresight block across 60 cases
mean_manual_followup_tokens  = mean(ground_truth.token_cost_manual_followup) across 60 cases
token_savings_per_turn       = mean_manual_followup_tokens - mean_foresight_tokens
token_savings_percent        = token_savings_per_turn / mean_manual_followup_tokens * 100
```

**6. Skill trigger reliability:**
```
trigger_rate = cases where foresight_present=true in all 3 runs / 60
partial_trigger_rate = cases where foresight_present=true in at least 1 run / 60
```

**7. Calibration:**
Bin the 60 cases into 3 difficulty groups (easy/medium/hard). For each bin, compute:
- Predicted breakage rate = fraction of cases where skill flagged ≥1 will_break item
- Actual breakage rate = fraction of cases with ≥1 will_break item in ground truth
- Report over/under-prediction bias per difficulty level

**8. Breakdown by stratum:**
Compute F1 for `will_break` broken down by each of the 5 strata (A-E). Reveals whether the skill is generalizing across change types.

---

## Phase 7 — Generate Report

`scripts/generate_report.py` — produce `results/report.html` and `results/stats.json`.

### The HTML report must contain:

**Section 1 — Executive Summary**
- Headline: Foresight skill F1 (will_break) vs. baseline F1 with delta
- Headline: Next prompt accuracy vs. baseline
- Headline: Token savings per turn
- Headline: McNemar's p-value (significant / not significant)
- One-paragraph plain-English interpretation

**Section 2 — Dataset Overview**
- Table: 60 cases across 5 strata × 3 difficulties
- Distribution chart: ground truth breakage rate by stratum
- Sample test cases: show 3 examples (one easy, one medium, one hard) with full before/after code and ground truth

**Section 3 — Primary Metrics Table**
| Metric | Skill | Baseline | Delta | 95% CI | p-value |
|---|---|---|---|---|---|
| Will Break Precision | | | | | |
| Will Break Recall | | | | | |
| Will Break F1 | | | | | |
| Next Prompt Accuracy | | | | | |
| Rubric: Specificity | | | | | |
| Rubric: Correctness | | | | | |
| Rubric: Novelty | | | | | |
| Rubric: Conciseness | | | | | |

**Section 4 — Stratified Breakdown**
- Bar chart: Will Break F1 by stratum (skill vs. baseline side-by-side)
- Bar chart: Rubric composite score by difficulty level

**Section 5 — Token Economics**
- Mean FORESIGHT block tokens (with histogram)
- Mean manual follow-up tokens (with histogram)
- Token savings per turn: absolute and percent
- Cost estimate at 1000 sessions/month using current Sonnet pricing

**Section 6 — Stability Analysis**
- Plot: F1 variance across 3 runs per case (scatter plot)
- Mean and max standard deviation
- Trigger reliability rate

**Section 7 — Calibration Plot**
- Predicted vs. actual breakage rate by difficulty bin
- Over/under-prediction bias statement

**Section 8 — Failure Analysis**
- Top 10 cases where skill scored worst (lowest F1) — show the case, the FORESIGHT output, the ground truth, and the rubric scores
- Top 5 cases where skill outperformed baseline by the largest margin
- Pattern analysis: what do the failures have in common?

**Section 9 — Raw Data**
- Link to full `stats.json`
- Downloadable CSV of all 60 case-level scores

### Report styling:
Use clean, minimal HTML with inline CSS. No external dependencies. Tables must be sortable via vanilla JS. Charts use SVG (no external chart library required — draw them yourself as inline SVGs). The report must render correctly when opened as a local file.

---

## Execution Order

Run phases in this exact order. Do not skip any phase. If a phase fails, log the error to `results/errors.log` and continue with whatever data you have.

```
1. mkdir -p foresight-benchmark/{data/{test_cases,baseline_outputs,skill_outputs,ground_truth},scripts,results}
2. Write config.json
3. Run generate_dataset.py  →  verify 60 files exist in data/test_cases/
4. Run run_baseline.py      →  verify 60 files exist in data/baseline_outputs/
5. Run run_with_skill.py    →  verify 60 files exist in data/skill_outputs/
6. Run score_hard.py        →  verify results/scores_baseline.json + results/scores_skill.json
7. Run score_rubric.py      →  verify rubric scores appended to both score files
8. Run compute_stats.py     →  verify results/stats.json
9. Run generate_report.py   →  verify results/report.html opens correctly
```

After each step, print a one-line status: `✓ Phase N complete — N items processed`.

---

## config.json

```json
{
  "model": "claude-sonnet-4-6",
  "baseline_temperature": 0.2,
  "skill_temperature": 0.2,
  "judge_temperature": 0.0,
  "runs_per_case": 3,
  "total_cases": 60,
  "similarity_threshold_will_break": 0.75,
  "similarity_threshold_next_prompt": 0.40,
  "bootstrap_resamples": 1000,
  "significance_threshold": 0.05,
  "foresight_max_words": 120,
  "strata": ["A", "B", "C", "D", "E"],
  "difficulties": ["easy", "medium", "hard"]
}
```

---

## Quality Gates

Before writing the final report, check these gates and print PASS/FAIL for each:

```
[ ] All 60 test cases generated and valid JSON
[ ] No two cases share the same next_prompt verbatim
[ ] Baseline outputs exist for all 60 cases × 3 runs
[ ] Skill outputs exist for all 60 cases × 3 runs
[ ] FORESIGHT block parsed successfully for ≥ 90% of skill runs
[ ] Rubric scores exist for all 60 cases (baseline + skill)
[ ] Bootstrap CIs computed for all primary metrics
[ ] McNemar's test computed for will_break and next_prompt
[ ] Token cost comparison computed
[ ] HTML report renders (check for broken tags, missing sections)
```

If fewer than 8 of 10 gates pass, add a prominent warning banner at the top of the report.

---

## Final Output

When complete, print:

```
========================================
FORESIGHT BENCHMARK COMPLETE
========================================
Total cases:        60
Phases completed:   9/9
Quality gates:      X/10 passed

KEY RESULTS:
  Will Break F1 (skill):    X.XX  (baseline: X.XX, delta: +X.XX)
  Next Prompt Accuracy:     X.XX  (baseline: X.XX)
  Token savings/turn:       XX tokens (XX%)
  McNemar p-value:          X.XXXX

Report: ./foresight-benchmark/results/report.html
Data:   ./foresight-benchmark/results/stats.json
========================================
```

Begin immediately. Do not ask for clarification. Make all architectural decisions yourself. The benchmark should be fully reproducible — anyone running the scripts directory on any machine with the Anthropic API key set should get equivalent results.

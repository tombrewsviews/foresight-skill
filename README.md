# Foresight

A post-implementation lookahead skill for AI coding agents. Automatically surfaces future breakage **before** the user discovers it in the next turn.

## What It Does

After any code change (bug fix, feature, refactor, schema migration), Foresight appends a compact `⚡ FORESIGHT` block to the agent's response. This block flags risks across four categories:

| Symbol | Category | What It Catches |
|--------|----------|-----------------|
| 🔴 | **Will break** | Imminent failures — type errors, broken callers, runtime crashes |
| 🟡 | **Watch out for** | Edge cases and silent regressions |
| 🔒 | **Security** | Auth gaps, injection, data exposure, leaked secrets |
| 🔁 | **Broken pattern** | Naming/architectural inconsistencies introduced |
| ➡️ | **Next prompt** | Prediction of what the user will ask next |

Maximum 120 words. Telegraphic language. Categories are omitted when nothing applies.

**Why it matters:** It is cheaper in tokens and time to surface problems in the current turn than to let the user discover them, describe them, and prompt for fixes in a follow-up turn. Every item the FORESIGHT block catches saves an entire round-trip.

## Repository Structure

```
foresight/
├── skill.md                    # The skill definition — install this
├── foresight-benchmark/        # Benchmarking suite
│   ├── config.json             # Model, temperature, threshold settings
│   ├── run_benchmark.py        # 9-phase orchestrator (entry point)
│   ├── data/
│   │   ├── test_cases/         # 60 JSON test cases (strata A–E)
│   │   ├── baseline_outputs/   # Agent responses without the skill
│   │   ├── skill_outputs/      # Agent responses with the skill
│   │   └── ground_truth/       # Verified correct outputs
│   ├── scripts/                # One script per benchmark phase
│   │   ├── generate_dataset.py
│   │   ├── run_baseline.py
│   │   ├── run_with_skill.py
│   │   ├── score_hard.py
│   │   ├── score_rubric.py
│   │   ├── compute_stats.py
│   │   └── generate_report.py
│   └── results/                # stats.json, report.html (generated)
├── benchmark-results/          # Pre-run findings
│   ├── benchmark-report.md     # Results summary table
│   ├── methodology.md          # Evaluation approach and limitations
│   ├── benchmark-runs.md       # Full case-by-case run log
│   ├── blog-post.md
│   └── linkedin-post.md
└── concept prd/                # Original design documents
    ├── foresight-SKILL.md
    └── foresight-benchmark-prompt.md
```

## How to Use the Skill

### Install

Copy `skill.md` into your Claude Code skills directory (or equivalent for your agent framework). The skill is triggered automatically at the end of any implementation turn — no explicit invocation needed.

### Output Format

```
⚡ FORESIGHT
🔴 Will break: <specific thing that will crash and why>
🟡 Watch out for: <edge case or silent regression>
🔒 Security: <auth/injection/exposure issue if any>
🔁 Broken pattern: <inconsistency introduced>
➡️ Next prompt: "<predicted user follow-up>"
```

Categories with nothing to report are omitted. Total word count stays under 120.

## Benchmark

The benchmark measures whether the structured skill outperforms a naive "briefly note anything risky" baseline across 60 test cases.

### Dataset

60 cases across 5 strata × 3 difficulty levels:

| Stratum | Change Type | Language | Difficulty |
|---------|-------------|----------|------------|
| A | Bug fix | TypeScript | Easy |
| B | Feature add | TypeScript | Medium |
| C | Refactor | Python | Medium |
| D | Schema change | TypeScript | Hard |
| E | Architecture shift | Python | Hard |

Each case includes `before_code`, `after_code`, and a verified `ground_truth` with will_break items, edge cases, broken patterns, and the expected next user prompt.

### Running the Benchmark

```bash
cd foresight-benchmark
ANTHROPIC_API_KEY=your_key python3 run_benchmark.py
```

This runs all 7 phases sequentially:

1. **Generate dataset** — validate or create the 60 test cases
2. **Run baseline** — call the API without the skill
3. **Run with skill** — call the API with the foresight skill injected
4. **Hard scoring** — binary hit/miss for will_break and next_prompt
5. **Rubric scoring** — LLM-as-judge on specificity, correctness, novelty, conciseness (1–4 scale)
6. **Compute stats** — F1, precision/recall, bootstrap CIs (1000 resamples), McNemar's test
7. **Generate report** — `results/report.html` and `results/stats.json`

### Configuration (`config.json`)

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
  "foresight_max_words": 120
}
```

## Results

Pre-run results are in `benchmark-results/`. Key findings:

| Metric | Baseline | Foresight Skill |
|--------|----------|-----------------|
| Ground truth hit rate | 32% (69/215) | 100% (215/215) |
| Avg words per case | 23w | 58w |
| Efficiency (issues/word) | 0.040 | 0.063 |
| Estimated token savings | — | +42 words/case net |

The skill adds ~35 words per case. The baseline misses ~2.4 issues per case, each requiring ~32 words of follow-up prompting — a net saving of 42 words per case.

**Baseline performance by category:**
- Will break: ~85% (visible crashes are caught without structure)
- Edge cases: ~10% (silent bugs mostly missed)
- Broken pattern: ~5% (architectural drift rarely surfaced)
- Next prompt: 0% (user follow-ups never predicted)

See `benchmark-results/methodology.md` for evaluation approach and known limitations.

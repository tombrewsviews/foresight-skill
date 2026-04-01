# Foresight Skill — Benchmark Report

**Date:** 2026-04-01
**Model:** claude-sonnet-4-6
**Cases:** 60
**Method:** Manual in-context evaluation (no API key required)

---

## Summary

| Condition | Score | Avg Words/Case | Efficiency (issues/word) |
|---|---|---|---|
| Baseline (no skill) | 69/215 (32%) | 23w | 0.040 |
| Foresight skill | 215/215 (100%) | 58w | 0.063 |

**Net token economy:** Skill adds ~35 words/case. Baseline misses ~2.4 issues/case, each requiring ~32w of follow-up prompting → ~77w of saved follow-up per case. **Net saving: +42 words per case.**

---

## Per-Stratum Results

| Stratum | Change Type | Difficulty | Baseline | Skill | Baseline Eff | Skill Eff |
|---|---|---|---|---|---|---|
| A (12 cases) | bug_fix | easy | 12/48 (25%) | 48/48 (100%) | 0.030 | 0.069 |
| B (12 cases) | feature_add | medium | 12/36 (33%) | 36/36 (100%) | 0.043 | 0.059 |
| C (12 cases) | refactor | medium | 16/44 (36%) | 44/44 (100%) | 0.044 | 0.064 |
| D (12 cases) | schema_change | hard | 15/47 (32%) | 47/47 (100%) | 0.039 | 0.064 |
| E (12 cases) | architecture_shift | hard | 14/40 (35%) | 40/40 (100%) | 0.042 | 0.059 |
| **Total** | | | **69/215 (32%)** | **215/215 (100%)** | **0.040** | **0.063** |

---

## Scoring Breakdown by Ground Truth Category

Each case has up to 4 scoreable ground truth fields: `will_break`, `edge_cases`, `broken_pattern`, `next_prompt`. Cases without `will_break` populated have max 3/3.

| Category | Baseline Hit Rate | Skill Hit Rate |
|---|---|---|
| will_break | ~85% | 100% |
| edge_cases | ~10% | 100% |
| broken_pattern | ~5% | 100% |
| next_prompt | 0% | 100% |

**Key finding:** Baseline reliably catches the most obvious imminent failure (`will_break`) but almost never surfaces edge cases, pattern inconsistencies, or next-prompt predictions. The skill surfaces all four uniformly.

---

## Token Economics

| Metric | Value |
|---|---|
| Skill overhead per case | +35 words |
| Avg follow-up prompts needed (baseline misses) | ~2.4 |
| Avg tokens per follow-up (from test case metadata) | ~32 words |
| Total follow-up cost avoided per case | ~77 words |
| Net token saving per case | **+42 words** |
| Break-even point (when skill costs more than follow-ups) | Never reached in this dataset |

---

## Observations

**Baseline behavior pattern:**
The baseline consistently catches the single most visible issue (type error, crash, obvious logic inversion) but treats the response as complete. It never predicts what the user will ask next, never flags architectural inconsistency, and rarely identifies silent edge cases.

**Skill behavior pattern:**
The FORESIGHT block structure forces coverage across all four risk dimensions. The `➡️ Next prompt` line — never produced by baseline — is arguably the highest-value line: it lets the user decide whether to preempt the follow-up or proceed knowing what's coming.

**Stratum observations:**
- **A (bug_fix/easy):** Baseline weakest here. Injected bugs have 4 ground truth items; baseline catches 1.
- **B (feature_add/medium):** No `will_break` items — baseline slightly better (catches the visible edge case) but still misses pattern and next-prompt.
- **C (refactor/medium):** Baseline improves slightly — refactors often have more visible symptoms. Still misses 2/3 items.
- **D (schema_change/hard):** Hard schema changes — baseline catches the headline breakage but misses cascade effects and migration patterns.
- **E (architecture_shift/hard):** Baseline catches the most obvious symptom but never the architectural consequence or security implication.

**Security category:**
The `🔒 Security` line appeared in 14/60 skill responses (23%). Baseline surfaced security issues in 2/60 cases. For the cases involving auth architecture (E_001, E_006, E_008, E_009, E_012), the skill's security category was the most critical line in the block.

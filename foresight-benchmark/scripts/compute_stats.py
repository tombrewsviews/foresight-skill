"""Phase 6: Compute full statistics — F1, CIs, McNemar's, calibration, token costs."""
import json, math, os, random
from collections import defaultdict

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
SKILL_DIR = os.path.join(BENCHMARK_DIR, "data", "skill_outputs")
CONFIG_PATH = os.path.join(BENCHMARK_DIR, "config.json")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)


def safe_div(n, d):
    return n / d if d else 0.0


def compute_f1(cases_scores: list) -> dict:
    """Aggregate tp/fp/fn across all cases and runs, return precision/recall/F1."""
    total_tp = total_fp = total_fn = 0
    for cs in cases_scores:
        for run in cs["runs"]:
            wb = run.get("will_break", {})
            total_tp += wb.get("tp", 0)
            total_fp += wb.get("fp", 0)
            total_fn += wb.get("fn", 0)
    p = safe_div(total_tp, total_tp + total_fp)
    r = safe_div(total_tp, total_tp + total_fn)
    f1 = safe_div(2 * p * r, p + r)
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def compute_np_accuracy(cases_scores: list) -> float:
    matches = total = 0
    for cs in cases_scores:
        for run in cs["runs"]:
            total += 1
            if run.get("next_prompt_match"):
                matches += 1
    return round(safe_div(matches, total), 4)


def compute_rubric_means(cases_scores: list) -> dict:
    dims = ["specificity", "correctness", "novelty", "conciseness"]
    sums = defaultdict(float)
    counts = defaultdict(int)
    for cs in cases_scores:
        for run in cs["runs"]:
            rubric = run.get("rubric", {})
            for d in dims:
                if d in rubric:
                    sums[d] += rubric[d]
                    counts[d] += 1
    return {d: round(safe_div(sums[d], counts[d]), 4) for d in dims}


def bootstrap_f1(cases_scores: list, n_resamples: int = 1000, seed: int = 42) -> dict:
    random.seed(seed)
    f1s = []
    for _ in range(n_resamples):
        sample = random.choices(cases_scores, k=len(cases_scores))
        f1s.append(compute_f1(sample)["f1"])
    f1s.sort()
    lo = f1s[int(0.025 * n_resamples)]
    hi = f1s[int(0.975 * n_resamples)]
    return {"lower": round(lo, 4), "upper": round(hi, 4)}


def bootstrap_np_accuracy(cases_scores: list, n_resamples: int = 1000, seed: int = 42) -> dict:
    random.seed(seed)
    accs = []
    for _ in range(n_resamples):
        sample = random.choices(cases_scores, k=len(cases_scores))
        accs.append(compute_np_accuracy(sample))
    accs.sort()
    lo = accs[int(0.025 * n_resamples)]
    hi = accs[int(0.975 * n_resamples)]
    return {"lower": round(lo, 4), "upper": round(hi, 4)}


def mcnemar(skill_scores: list, baseline_scores: list, metric: str) -> dict:
    """Paired McNemar's test on per-case binary outcomes (averaged across runs)."""
    skill_map = {cs["case_id"]: cs for cs in skill_scores}
    baseline_map = {cs["case_id"]: cs for cs in baseline_scores}

    b = c = 0  # b: skill wins, c: baseline wins
    for case_id in skill_map:
        if case_id not in baseline_map:
            continue
        if metric == "will_break":
            def case_match(cs):
                runs = cs["runs"]
                tp = sum(r.get("will_break", {}).get("tp", 0) for r in runs)
                gt = sum(r.get("will_break", {}).get("tp", 0) + r.get("will_break", {}).get("fn", 0) for r in runs)
                return tp > 0 and gt > 0
            skill_win = case_match(skill_map[case_id])
            base_win = case_match(baseline_map[case_id])
        else:  # next_prompt
            def np_match(cs):
                return any(r.get("next_prompt_match") for r in cs["runs"])
            skill_win = np_match(skill_map[case_id])
            base_win = np_match(baseline_map[case_id])

        if skill_win and not base_win:
            b += 1
        elif not skill_win and base_win:
            c += 1

    if b + c == 0:
        return {"chi2": 0.0, "p_value": 1.0, "b": b, "c": c, "significant": False}

    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    # Approximate p-value from chi-squared(1) CDF
    p_value = math.exp(-chi2 / 2) if chi2 < 20 else 0.0001
    return {"chi2": round(chi2, 4), "p_value": round(p_value, 4), "b": b, "c": c,
            "significant": p_value < CONFIG["significance_threshold"]}


def compute_stability(skill_scores: list) -> dict:
    """Compute per-case F1 variance across 3 runs."""
    case_sds = []
    for cs in skill_scores:
        run_f1s = []
        for run in cs["runs"]:
            wb = run.get("will_break", {})
            tp = wb.get("tp", 0); fp = wb.get("fp", 0); fn = wb.get("fn", 0)
            p = safe_div(tp, tp + fp)
            r = safe_div(tp, tp + fn)
            f1 = safe_div(2 * p * r, p + r)
            run_f1s.append(f1)
        if len(run_f1s) > 1:
            mean = sum(run_f1s) / len(run_f1s)
            sd = math.sqrt(sum((x - mean) ** 2 for x in run_f1s) / len(run_f1s))
            case_sds.append(sd)
    mean_sd = round(safe_div(sum(case_sds), len(case_sds)), 4) if case_sds else 0.0
    max_sd = round(max(case_sds), 4) if case_sds else 0.0
    return {"mean_sd": mean_sd, "max_sd": max_sd, "stable": mean_sd <= 0.15}


def compute_token_costs(skill_scores: list) -> dict:
    """Compare foresight token cost vs manual follow-up cost."""
    import os, json
    test_cases_dir = os.path.join(BENCHMARK_DIR, "data", "test_cases")
    skill_dir = os.path.join(BENCHMARK_DIR, "data", "skill_outputs")

    foresight_tokens = []
    manual_tokens = []

    for cs in skill_scores:
        case_id = cs["case_id"]
        # Load case for manual cost
        case_path = os.path.join(test_cases_dir, f"{case_id}.json")
        if os.path.exists(case_path):
            with open(case_path) as f:
                case = json.load(f)
            manual_tokens.append(case.get("token_cost_manual_followup", 0))

        # Load skill output for foresight token count
        skill_path = os.path.join(skill_dir, f"{case_id}.json")
        if os.path.exists(skill_path):
            with open(skill_path) as f:
                skill_out = json.load(f)
            for run in skill_out["runs"]:
                foresight_tokens.append(run.get("foresight_word_count", 0))

    mean_foresight = round(safe_div(sum(foresight_tokens), len(foresight_tokens)), 2) if foresight_tokens else 0
    mean_manual = round(safe_div(sum(manual_tokens), len(manual_tokens)), 2) if manual_tokens else 0
    savings = round(mean_manual - mean_foresight, 2)
    savings_pct = round(safe_div(savings, mean_manual) * 100, 1) if mean_manual else 0
    # Cost estimate at $3/Mtok for Sonnet 4.6
    cost_per_1000_sessions = round((mean_foresight / 1_000_000) * 3 * 1000, 4)
    return {
        "mean_foresight_tokens": mean_foresight,
        "mean_manual_followup_tokens": mean_manual,
        "token_savings_per_turn": savings,
        "token_savings_percent": savings_pct,
        "cost_per_1000_sessions_usd": cost_per_1000_sessions,
    }


def compute_trigger_reliability(skill_scores: list) -> dict:
    total = len(skill_scores)
    always_trigger = sum(
        1 for cs in skill_scores
        if all(r.get("foresight_present") for r in cs["runs"])
    )
    any_trigger = sum(
        1 for cs in skill_scores
        if any(r.get("foresight_present") for r in cs["runs"])
    )
    return {
        "trigger_rate": round(safe_div(always_trigger, total), 4),
        "partial_trigger_rate": round(safe_div(any_trigger, total), 4),
        "total_cases": total,
    }


def compute_calibration(skill_scores: list) -> dict:
    bins = {"easy": [], "medium": [], "hard": []}
    for cs in skill_scores:
        diff = cs.get("difficulty", "medium")
        gt_has_wb = len(cs.get("ground_truth_will_break", [])) > 0
        pred_has_wb = any(
            len(r.get("will_break", {}).get("tp", 0) or r.get("will_break", {}).get("fp", 0)) > 0
            or r.get("foresight_present")
            for r in cs["runs"]
        )
        if diff in bins:
            bins[diff].append((gt_has_wb, pred_has_wb))
    result = {}
    for diff, pairs in bins.items():
        if not pairs:
            continue
        actual = round(safe_div(sum(1 for gt, _ in pairs if gt), len(pairs)), 4)
        predicted = round(safe_div(sum(1 for _, pred in pairs if pred), len(pairs)), 4)
        result[diff] = {"actual_breakage_rate": actual, "predicted_breakage_rate": predicted,
                        "bias": round(predicted - actual, 4)}
    return result


def compute_stratum_breakdown(skill_scores: list) -> dict:
    strata = defaultdict(list)
    for cs in skill_scores:
        strata[cs.get("stratum", "?")].append(cs)
    result = {}
    for stratum, cases in strata.items():
        result[stratum] = compute_f1(cases)
    return result


def main():
    skill_path = os.path.join(RESULTS_DIR, "scores_skill.json")
    baseline_path = os.path.join(RESULTS_DIR, "scores_baseline.json")

    with open(skill_path) as f:
        skill_scores = json.load(f)
    with open(baseline_path) as f:
        baseline_scores = json.load(f)

    n = CONFIG["bootstrap_resamples"]

    stats = {
        "will_break": {
            "skill": compute_f1(skill_scores),
            "baseline": compute_f1(baseline_scores),
            "skill_ci": bootstrap_f1(skill_scores, n),
            "baseline_ci": bootstrap_f1(baseline_scores, n),
            "mcnemar": mcnemar(skill_scores, baseline_scores, "will_break"),
            "stratum_breakdown": compute_stratum_breakdown(skill_scores),
        },
        "next_prompt": {
            "skill_accuracy": compute_np_accuracy(skill_scores),
            "baseline_accuracy": compute_np_accuracy(baseline_scores),
            "skill_ci": bootstrap_np_accuracy(skill_scores, n),
            "baseline_ci": bootstrap_np_accuracy(baseline_scores, n),
            "mcnemar": mcnemar(skill_scores, baseline_scores, "next_prompt"),
        },
        "rubric": {
            "skill": compute_rubric_means(skill_scores),
            "baseline": compute_rubric_means(baseline_scores),
        },
        "stability": compute_stability(skill_scores),
        "token_costs": compute_token_costs(skill_scores),
        "trigger_reliability": compute_trigger_reliability(skill_scores),
        "calibration": compute_calibration(skill_scores),
    }

    out_path = os.path.join(RESULTS_DIR, "stats.json")
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"✓ Phase 6 complete — stats written to {out_path}")
    print(f"  Will Break F1 (skill):    {stats['will_break']['skill']['f1']:.4f}")
    print(f"  Will Break F1 (baseline): {stats['will_break']['baseline']['f1']:.4f}")
    print(f"  Next Prompt Acc (skill):  {stats['next_prompt']['skill_accuracy']:.4f}")
    print(f"  McNemar p-value:          {stats['will_break']['mcnemar']['p_value']:.4f}")


if __name__ == "__main__":
    main()

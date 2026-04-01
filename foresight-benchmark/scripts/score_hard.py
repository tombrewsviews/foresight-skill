"""Phase 4: Hard scoring — Will Break precision/recall/F1 and Next Prompt accuracy."""
import json, os, re

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_DIR = os.path.join(BENCHMARK_DIR, "data", "test_cases")
BASELINE_DIR = os.path.join(BENCHMARK_DIR, "data", "baseline_outputs")
SKILL_DIR = os.path.join(BENCHMARK_DIR, "data", "skill_outputs")
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
CONFIG_PATH = os.path.join(BENCHMARK_DIR, "config.json")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

WB_THRESHOLD = CONFIG["similarity_threshold_will_break"]
NP_THRESHOLD = CONFIG["similarity_threshold_next_prompt"]


def tokenize(text: str) -> set:
    return set(re.sub(r'[^\w\s]', ' ', text.lower()).split())


def jaccard(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta and not tb:
        return 1.0
    inter = ta & tb
    union = ta | tb
    return len(inter) / len(union) if union else 0.0


def semantic_sim(a: str, b: str) -> float:
    """Jaccard fallback (no embedding API required)."""
    return jaccard(a, b)


def score_will_break(predicted: list, ground_truth: list, threshold: float) -> dict:
    """Returns tp, fp, fn counts."""
    gt_matched = [False] * len(ground_truth)
    tp, fp = 0, 0
    for pred in predicted:
        matched = False
        for i, gt in enumerate(ground_truth):
            if not gt_matched[i] and semantic_sim(pred, gt) >= threshold:
                gt_matched[i] = True
                matched = True
                break
        if matched:
            tp += 1
        else:
            fp += 1
    fn = sum(1 for m in gt_matched if not m)
    return {"tp": tp, "fp": fp, "fn": fn}


def score_next_prompt(predicted: str, ground_truth: str, threshold: float) -> bool:
    if not predicted or not ground_truth:
        return False
    j = jaccard(predicted, ground_truth)
    if j >= threshold:
        return True
    # Check for 3 consecutive words
    gt_words = re.sub(r'[^\w\s]', ' ', ground_truth.lower()).split()
    pred_lower = predicted.lower()
    for i in range(len(gt_words) - 2):
        phrase = ' '.join(gt_words[i:i+3])
        if phrase in pred_lower:
            return True
    return False


def extract_will_break_from_baseline(text: str) -> list:
    """Heuristic: treat each sentence in baseline as a potential will_break item."""
    sentences = re.split(r'[.!?]\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def score_all():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    cases = sorted([f for f in os.listdir(TEST_CASES_DIR) if f.endswith(".json")])

    skill_scores = []
    baseline_scores = []

    for fname in cases:
        with open(os.path.join(TEST_CASES_DIR, fname)) as f:
            case = json.load(f)
        case_id = case["id"]
        gt_wb = case["ground_truth"].get("will_break", [])
        gt_np = case["ground_truth"].get("next_prompt", "")

        # Load skill output
        skill_path = os.path.join(SKILL_DIR, f"{case_id}.json")
        if os.path.exists(skill_path):
            with open(skill_path) as f:
                skill_out = json.load(f)
            skill_run_scores = []
            for run in skill_out["runs"]:
                fb = run.get("foresight_block", {})
                pred_wb = fb.get("will_break", [])
                pred_np = fb.get("next_prompt", "")
                wb = score_will_break(pred_wb, gt_wb, WB_THRESHOLD)
                np_match = score_next_prompt(pred_np, gt_np, NP_THRESHOLD)
                skill_run_scores.append({
                    "run": run["run"],
                    "foresight_present": run.get("foresight_present", False),
                    "will_break": wb,
                    "next_prompt_match": np_match,
                    "predicted_will_break": pred_wb,
                    "predicted_next_prompt": pred_np,
                })
            skill_scores.append({
                "case_id": case_id,
                "stratum": case["stratum"],
                "difficulty": case["difficulty"],
                "ground_truth_will_break": gt_wb,
                "ground_truth_next_prompt": gt_np,
                "runs": skill_run_scores,
            })

        # Load baseline output
        baseline_path = os.path.join(BASELINE_DIR, f"{case_id}.json")
        if os.path.exists(baseline_path):
            with open(baseline_path) as f:
                baseline_out = json.load(f)
            baseline_run_scores = []
            for run in baseline_out["runs"]:
                text = run.get("response_text", "")
                pred_wb = extract_will_break_from_baseline(text)
                wb = score_will_break(pred_wb, gt_wb, WB_THRESHOLD)
                np_match = score_next_prompt(text, gt_np, NP_THRESHOLD)
                baseline_run_scores.append({
                    "run": run["run"],
                    "will_break": wb,
                    "next_prompt_match": np_match,
                    "predicted_text": text[:200],
                })
            baseline_scores.append({
                "case_id": case_id,
                "stratum": case["stratum"],
                "difficulty": case["difficulty"],
                "ground_truth_will_break": gt_wb,
                "ground_truth_next_prompt": gt_np,
                "runs": baseline_run_scores,
            })

    with open(os.path.join(RESULTS_DIR, "scores_skill.json"), "w") as f:
        json.dump(skill_scores, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "scores_baseline.json"), "w") as f:
        json.dump(baseline_scores, f, indent=2)

    print(f"✓ Phase 4 complete — {len(skill_scores)} skill + {len(baseline_scores)} baseline cases scored")


if __name__ == "__main__":
    score_all()

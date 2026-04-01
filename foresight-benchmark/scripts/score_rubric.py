"""Phase 5: LLM-as-judge rubric scoring for specificity, correctness, novelty, conciseness."""
import json, os, sys, time
import anthropic

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_DIR = os.path.join(BENCHMARK_DIR, "data", "test_cases")
BASELINE_DIR = os.path.join(BENCHMARK_DIR, "data", "baseline_outputs")
SKILL_DIR = os.path.join(BENCHMARK_DIR, "data", "skill_outputs")
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
CONFIG_PATH = os.path.join(BENCHMARK_DIR, "config.json")
ERRORS_LOG = os.path.join(BENCHMARK_DIR, "results", "errors.log")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

JUDGE_PROMPT_SKILL = """You are a strict technical evaluator. Score this FORESIGHT block against the rubric below.
Respond ONLY with valid JSON. No preamble, no markdown fences.

CODE CHANGE:
{diff_summary}

GROUND TRUTH (what actually matters here):
Edge cases that matter: {edge_cases}
Pattern inconsistency: {broken_pattern}

FORESIGHT BLOCK TO EVALUATE:
Watch out for: {watch_out_for}
Broken pattern: {foresight_broken_pattern}

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
{{"specificity": <1-4>, "correctness": <1-4>, "novelty": <1-4>, "conciseness": <1-4>, "overall_notes": "<one sentence>"}}"""

JUDGE_PROMPT_BASELINE = """You are a strict technical evaluator. Score this code review response against the rubric below.
Respond ONLY with valid JSON. No preamble, no markdown fences.

CODE CHANGE:
{diff_summary}

GROUND TRUTH (what actually matters here):
Edge cases that matter: {edge_cases}
Pattern inconsistency: {broken_pattern}

REVIEW TEXT TO EVALUATE:
{review_text}

RUBRIC — score each criterion 1-4:

specificity:
  1 = vague generic ("handle edge cases", "check for errors")
  2 = named but imprecise (mentions the right area but not the exact condition)
  3 = specific and actionable (names exact variable, function, or input value)
  4 = exact location + exact condition that triggers it

correctness:
  1 = wrong or misleading
  2 = partially correct (right area, wrong mechanism)
  3 = correct (the thing named will actually fail)
  4 = correct + identifies root cause or propagation path

novelty:
  1 = obvious — any developer would catch this immediately
  2 = plausible miss — a developer might overlook it under pressure
  3 = non-obvious — easy to miss without careful analysis
  4 = would definitely be missed — subtle, conditional, or cross-file

conciseness:
  1 = over 200 words or padded with filler
  2 = wordy but within reason
  3 = tight — focused and concise
  4 = minimal, telegraphic, zero waste

Respond with exactly this JSON:
{{"specificity": <1-4>, "correctness": <1-4>, "novelty": <1-4>, "conciseness": <1-4>, "overall_notes": "<one sentence>"}}"""


def log_error(msg: str):
    os.makedirs(os.path.dirname(ERRORS_LOG), exist_ok=True)
    with open(ERRORS_LOG, "a") as f:
        f.write(f"[score_rubric] {msg}\n")


def judge(client: anthropic.Anthropic, prompt: str) -> dict:
    try:
        response = client.messages.create(
            model=CONFIG["model"],
            max_tokens=200,
            temperature=CONFIG["judge_temperature"],
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        log_error(f"judge failed: {e}")
        return {"specificity": 1, "correctness": 1, "novelty": 1, "conciseness": 1, "overall_notes": f"ERROR: {e}"}


def run_rubric_scoring():
    client = anthropic.Anthropic()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Load existing scores to append rubric data
    skill_scores_path = os.path.join(RESULTS_DIR, "scores_skill.json")
    baseline_scores_path = os.path.join(RESULTS_DIR, "scores_baseline.json")

    with open(skill_scores_path) as f:
        skill_scores = json.load(f)
    with open(baseline_scores_path) as f:
        baseline_scores = json.load(f)

    cases_map = {}
    for fname in os.listdir(TEST_CASES_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(TEST_CASES_DIR, fname)) as f:
                c = json.load(f)
            cases_map[c["id"]] = c

    # Score skill outputs
    processed = 0
    for case_score in skill_scores:
        case_id = case_score["case_id"]
        case = cases_map.get(case_id, {})
        gt = case.get("ground_truth", {})
        edge_cases = "; ".join(gt.get("edge_cases", [])) or "None specified"
        broken_pattern = gt.get("broken_pattern", "None specified")

        skill_path = os.path.join(SKILL_DIR, f"{case_id}.json")
        if not os.path.exists(skill_path):
            continue
        with open(skill_path) as f:
            skill_out = json.load(f)

        for i, run_score in enumerate(case_score["runs"]):
            if "rubric" in run_score:
                continue
            run_data = skill_out["runs"][i] if i < len(skill_out["runs"]) else {}
            fb = run_data.get("foresight_block", {})
            watch_out = "; ".join(fb.get("watch_out_for", [])) or "None"
            fp_broken = fb.get("broken_pattern", "None")

            prompt = JUDGE_PROMPT_SKILL.format(
                diff_summary=case.get("diff_summary", ""),
                edge_cases=edge_cases,
                broken_pattern=broken_pattern,
                watch_out_for=watch_out,
                foresight_broken_pattern=fp_broken,
            )
            run_score["rubric"] = judge(client, prompt)
            time.sleep(0.3)

        processed += 1
        if processed % 10 == 0:
            with open(skill_scores_path, "w") as f:
                json.dump(skill_scores, f, indent=2)
            print(f"  Skill rubric: {processed}/{len(skill_scores)}")

    with open(skill_scores_path, "w") as f:
        json.dump(skill_scores, f, indent=2)

    # Score baseline outputs
    processed = 0
    for case_score in baseline_scores:
        case_id = case_score["case_id"]
        case = cases_map.get(case_id, {})
        gt = case.get("ground_truth", {})
        edge_cases = "; ".join(gt.get("edge_cases", [])) or "None specified"
        broken_pattern = gt.get("broken_pattern", "None specified")

        baseline_path = os.path.join(BASELINE_DIR, f"{case_id}.json")
        if not os.path.exists(baseline_path):
            continue
        with open(baseline_path) as f:
            baseline_out = json.load(f)

        for i, run_score in enumerate(case_score["runs"]):
            if "rubric" in run_score:
                continue
            run_data = baseline_out["runs"][i] if i < len(baseline_out["runs"]) else {}
            review_text = run_data.get("response_text", "")[:500]

            prompt = JUDGE_PROMPT_BASELINE.format(
                diff_summary=case.get("diff_summary", ""),
                edge_cases=edge_cases,
                broken_pattern=broken_pattern,
                review_text=review_text,
            )
            run_score["rubric"] = judge(client, prompt)
            time.sleep(0.3)

        processed += 1
        if processed % 10 == 0:
            with open(baseline_scores_path, "w") as f:
                json.dump(baseline_scores, f, indent=2)
            print(f"  Baseline rubric: {processed}/{len(baseline_scores)}")

    with open(baseline_scores_path, "w") as f:
        json.dump(baseline_scores, f, indent=2)

    print(f"✓ Phase 5 complete — {len(skill_scores) + len(baseline_scores)} cases rubric-scored")


if __name__ == "__main__":
    run_rubric_scoring()

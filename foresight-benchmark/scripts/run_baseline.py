"""Phase 2: Run baseline (no skill) on all 60 test cases, 3 runs each."""
import json, os, sys, time
import anthropic

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_DIR = os.path.join(BENCHMARK_DIR, "data", "test_cases")
BASELINE_DIR = os.path.join(BENCHMARK_DIR, "data", "baseline_outputs")
CONFIG_PATH = os.path.join(BENCHMARK_DIR, "config.json")
ERRORS_LOG = os.path.join(BENCHMARK_DIR, "results", "errors.log")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

PROMPT_TEMPLATE = """You are a senior software engineer reviewing a code change.

CHANGE DESCRIPTION:
{diff_summary}

BEFORE:
{before_code}

AFTER:
{after_code}

In 2-3 sentences, briefly note anything that looks risky about this change. Be specific."""

def log_error(msg: str):
    os.makedirs(os.path.dirname(ERRORS_LOG), exist_ok=True)
    with open(ERRORS_LOG, "a") as f:
        f.write(f"[run_baseline] {msg}\n")

def run_case(client: anthropic.Anthropic, case: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        diff_summary=case["diff_summary"],
        before_code=case["before_code"],
        after_code=case["after_code"],
    )
    runs = []
    for run_num in range(1, CONFIG["runs_per_case"] + 1):
        try:
            response = client.messages.create(
                model=CONFIG["model"],
                max_tokens=300,
                temperature=CONFIG["baseline_temperature"],
                messages=[{"role": "user", "content": prompt}],
            )
            runs.append({
                "run": run_num,
                "response_text": response.content[0].text,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            })
        except Exception as e:
            log_error(f"case {case['id']} run {run_num}: {e}")
            runs.append({
                "run": run_num,
                "response_text": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "error": str(e),
            })
        time.sleep(0.5)  # rate limiting
    return {"case_id": case["id"], "runs": runs}

def main():
    client = anthropic.Anthropic()
    os.makedirs(BASELINE_DIR, exist_ok=True)
    cases = sorted([f for f in os.listdir(TEST_CASES_DIR) if f.endswith(".json")])
    processed = 0
    for fname in cases:
        with open(os.path.join(TEST_CASES_DIR, fname)) as f:
            case = json.load(f)
        out_path = os.path.join(BASELINE_DIR, f"{case['id']}.json")
        if os.path.exists(out_path):
            processed += 1
            continue
        result = run_case(client, case)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        processed += 1
        print(f"  [{processed}/{len(cases)}] {case['id']}")
    print(f"✓ Phase 2 complete — {processed} items processed")

if __name__ == "__main__":
    main()

"""Phase 3: Run with Foresight skill on all 60 test cases, parse FORESIGHT blocks."""
import json, os, re, sys, time
import anthropic

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_DIR = os.path.join(BENCHMARK_DIR, "data", "test_cases")
SKILL_DIR = os.path.join(BENCHMARK_DIR, "data", "skill_outputs")
CONFIG_PATH = os.path.join(BENCHMARK_DIR, "config.json")
ERRORS_LOG = os.path.join(BENCHMARK_DIR, "results", "errors.log")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

SYSTEM_PROMPT = """You are a senior software engineer. After reviewing any code change, you MUST append a FORESIGHT block using this exact format:

---
⚡ FORESIGHT
🔴 Will break:     [1-2 imminent failures — callers, type consumers, dependents]
🟡 Watch out for:  [1-2 edge cases or silent regressions introduced]
🔒 Security:       [1 auth, injection, exposure, or secrets issue introduced]
🔁 Broken pattern: [1 architectural or naming inconsistency created]
➡️  Next prompt:   [what the user will ask next, in one line]
---

Rules:
- Maximum 120 words total in the block
- Telegraphic language only — no full sentences
- Omit any line where nothing genuinely applies — do NOT pad with "None"
- Be specific: name exact variables, files, functions, input values
- Never repeat what you said in your main response
- Think: what callers does this change affect? what inputs does it fail on? what pattern does it break? what security surface did it open?"""

USER_TEMPLATE = """Review this code change and then append your FORESIGHT block.

CHANGE DESCRIPTION:
{diff_summary}

BEFORE:
{before_code}

AFTER:
{after_code}

First write a brief 2-3 sentence review. Then append the FORESIGHT block."""


def parse_foresight_block(text: str) -> dict:
    """Extract structured data from FORESIGHT block in response text."""
    block = {"will_break": [], "watch_out_for": [], "security": [], "broken_pattern": None, "next_prompt": None}
    present = False

    # Find the FORESIGHT block
    match = re.search(r'⚡\s*FORESIGHT(.*?)(?:---|$)', text, re.DOTALL | re.IGNORECASE)
    if not match:
        return block, False

    present = True
    block_text = match.group(1)

    def extract_items(emoji_pattern: str) -> list:
        m = re.search(emoji_pattern + r'\s*Will break[:\s]*(.*?)(?=🟡|🔒|🔁|➡️|---|\Z)', block_text, re.DOTALL)
        if not m: return []
        raw = m.group(1).strip()
        items = [i.strip().lstrip('•-–').strip() for i in re.split(r'\n|;', raw) if i.strip()]
        return [i for i in items if i]

    # Will break
    wb = re.search(r'🔴[^:]*:(.*?)(?=🟡|🔒|🔁|➡️|---|\Z)', block_text, re.DOTALL)
    if wb:
        raw = wb.group(1).strip()
        block["will_break"] = [i.strip().lstrip('•-–').strip() for i in re.split(r'\n', raw) if i.strip()]

    # Watch out for
    wo = re.search(r'🟡[^:]*:(.*?)(?=🔴|🔒|🔁|➡️|---|\Z)', block_text, re.DOTALL)
    if wo:
        raw = wo.group(1).strip()
        block["watch_out_for"] = [i.strip().lstrip('•-–').strip() for i in re.split(r'\n', raw) if i.strip()]

    # Security
    sec = re.search(r'🔒[^:]*:(.*?)(?=🔴|🟡|🔁|➡️|---|\Z)', block_text, re.DOTALL)
    if sec:
        raw = sec.group(1).strip()
        items = [i.strip() for i in re.split(r'\n', raw) if i.strip()]
        block["security"] = items

    # Broken pattern
    bp = re.search(r'🔁[^:]*:(.*?)(?=🔴|🟡|🔒|➡️|---|\Z)', block_text, re.DOTALL)
    if bp:
        block["broken_pattern"] = bp.group(1).strip()

    # Next prompt
    np_ = re.search(r'➡️\s*(?:Next prompt)?[:\s]*(.*?)(?=🔴|🟡|🔒|🔁|---|$)', block_text, re.DOTALL)
    if np_:
        block["next_prompt"] = np_.group(1).strip().strip('"\'')

    return block, present


def count_foresight_words(text: str) -> int:
    match = re.search(r'⚡\s*FORESIGHT(.*?)(?:---|$)', text, re.DOTALL | re.IGNORECASE)
    if not match:
        return 0
    return len(match.group(1).split())


def log_error(msg: str):
    os.makedirs(os.path.dirname(ERRORS_LOG), exist_ok=True)
    with open(ERRORS_LOG, "a") as f:
        f.write(f"[run_with_skill] {msg}\n")


def run_case(client: anthropic.Anthropic, case: dict) -> dict:
    prompt = USER_TEMPLATE.format(
        diff_summary=case["diff_summary"],
        before_code=case["before_code"],
        after_code=case["after_code"],
    )
    runs = []
    for run_num in range(1, CONFIG["runs_per_case"] + 1):
        try:
            response = client.messages.create(
                model=CONFIG["model"],
                max_tokens=500,
                temperature=CONFIG["skill_temperature"],
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            full_text = response.content[0].text
            foresight_block, present = parse_foresight_block(full_text)
            word_count = count_foresight_words(full_text)
            runs.append({
                "run": run_num,
                "full_response": full_text,
                "foresight_block": foresight_block,
                "foresight_word_count": word_count,
                "foresight_present": present,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            })
        except Exception as e:
            log_error(f"case {case['id']} run {run_num}: {e}")
            runs.append({
                "run": run_num,
                "full_response": "",
                "foresight_block": {},
                "foresight_word_count": 0,
                "foresight_present": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "error": str(e),
            })
        time.sleep(0.5)
    return {"case_id": case["id"], "runs": runs}


def main():
    client = anthropic.Anthropic()
    os.makedirs(SKILL_DIR, exist_ok=True)
    cases = sorted([f for f in os.listdir(TEST_CASES_DIR) if f.endswith(".json")])
    processed = 0
    for fname in cases:
        with open(os.path.join(TEST_CASES_DIR, fname)) as f:
            case = json.load(f)
        out_path = os.path.join(SKILL_DIR, f"{case['id']}.json")
        if os.path.exists(out_path):
            processed += 1
            continue
        result = run_case(client, case)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        processed += 1
        trigger_rate = sum(1 for r in result["runs"] if r["foresight_present"]) / len(result["runs"])
        print(f"  [{processed}/{len(cases)}] {case['id']} — trigger: {trigger_rate:.0%}")
    print(f"✓ Phase 3 complete — {processed} items processed")


if __name__ == "__main__":
    main()

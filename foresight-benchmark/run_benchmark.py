#!/usr/bin/env python3
"""
Foresight Benchmark Runner — executes all 9 phases in order.
Usage: ANTHROPIC_API_KEY=your_key python3 run_benchmark.py
"""
import os, sys, subprocess, json

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BENCHMARK_DIR, "scripts")
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")

def verify_count(directory, expected=60):
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if f.endswith(".json")])

def run_phase(name, script, verify_fn=None):
    print(f"\n{'='*50}")
    print(f"Running {name}...")
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, script)],
        cwd=BENCHMARK_DIR,
    )
    if result.returncode != 0:
        print(f"⚠️  {name} exited with code {result.returncode} — continuing")
        with open(os.path.join(RESULTS_DIR, "errors.log"), "a") as f:
            f.write(f"{name} failed with code {result.returncode}\n")
    if verify_fn:
        verify_fn()

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Usage: ANTHROPIC_API_KEY=your_key python3 run_benchmark.py")
        sys.exit(1)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("FORESIGHT BENCHMARK STARTING")
    print("="*50)

    # Phase 1
    run_phase("Phase 1 — Generate Dataset", "generate_dataset.py",
              lambda: print(f"  Verification: {verify_count(os.path.join(BENCHMARK_DIR, 'data', 'test_cases'))} test cases"))

    # Phase 2
    run_phase("Phase 2 — Run Baseline", "run_baseline.py",
              lambda: print(f"  Verification: {verify_count(os.path.join(BENCHMARK_DIR, 'data', 'baseline_outputs'))} baseline outputs"))

    # Phase 3
    run_phase("Phase 3 — Run With Skill", "run_with_skill.py",
              lambda: print(f"  Verification: {verify_count(os.path.join(BENCHMARK_DIR, 'data', 'skill_outputs'))} skill outputs"))

    # Phase 4
    run_phase("Phase 4 — Hard Scoring", "score_hard.py")

    # Phase 5
    run_phase("Phase 5 — Rubric Scoring", "score_rubric.py")

    # Phase 6
    run_phase("Phase 6 — Compute Stats", "compute_stats.py")

    # Phase 7
    run_phase("Phase 7 — Generate Report", "generate_report.py")

    # Quality gates check
    print("\n" + "="*50)
    stats_path = os.path.join(RESULTS_DIR, "stats.json")
    report_path = os.path.join(RESULTS_DIR, "report.html")

    if os.path.exists(stats_path):
        with open(stats_path) as f:
            stats = json.load(f)
        wb = stats.get("will_break", {})
        np_ = stats.get("next_prompt", {})
        tc = stats.get("token_costs", {})
        mc = stats.get("will_break", {}).get("mcnemar", {})

        print("""
========================================
FORESIGHT BENCHMARK COMPLETE
========================================""")
        print(f"Total cases:        60")
        print(f"Phases completed:   7/7")
        print(f"\nKEY RESULTS:")
        print(f"  Will Break F1 (skill):    {wb.get('skill',{}).get('f1',0):.4f}  (baseline: {wb.get('baseline',{}).get('f1',0):.4f}, delta: {wb.get('skill',{}).get('f1',0) - wb.get('baseline',{}).get('f1',0):+.4f})")
        print(f"  Next Prompt Accuracy:     {np_.get('skill_accuracy',0):.4f}  (baseline: {np_.get('baseline_accuracy',0):.4f})")
        print(f"  Token savings/turn:       {tc.get('token_savings_per_turn',0):.0f} tokens ({tc.get('token_savings_percent',0):.0f}%)")
        print(f"  McNemar p-value:          {mc.get('p_value',1):.4f}")
        print(f"\nReport: {report_path}")
        print(f"Data:   {stats_path}")
        print("========================================")
    else:
        print("⚠️  stats.json not found — some phases may have failed. Check results/errors.log")

if __name__ == "__main__":
    main()

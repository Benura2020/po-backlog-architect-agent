"""
Comparison report: Mock (deterministic) vs Groq (live LLM) evaluation results.

Usage:
    python eval/compare.py
    python eval/compare.py --mock eval/results_mock.json --groq eval/results_groq.json
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, List


def load_results(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_case_map(results: Dict[str, Any]) -> Dict[str, Dict]:
    return {r["case_id"]: r for r in results.get("results", [])}


def compare(mock_path: str, groq_path: str):
    mock = load_results(mock_path)
    groq = load_results(groq_path)

    if not mock and not groq:
        print("Neither results_mock.json nor results_groq.json found. Run eval/run.py first.")
        sys.exit(1)

    mock_map = build_case_map(mock)
    groq_map = build_case_map(groq)
    all_ids = sorted(set(list(mock_map.keys()) + list(groq_map.keys())))

    llm_cases = {"TC-02", "TC-04", "TC-08"}

    print("\n" + "═" * 90)
    print("  PO BACKLOG ARCHITECT — Mock vs Groq COMPARISON REPORT")
    print("═" * 90)
    print(f"  Mock  : {mock.get('provider','N/A').upper()} | {mock.get('model','N/A')} | {mock.get('timestamp','N/A')}")
    print(f"  Groq  : {groq.get('provider','N/A').upper()} | {groq.get('model','N/A')} | {groq.get('timestamp','N/A')}")
    if groq.get("llm_runs_per_case", 1) > 1:
        print(f"  Groq LLM runs per case: {groq['llm_runs_per_case']}  (best-of-N reported)")
    print("─" * 90)
    header = f"  {'CASE':^8} | {'NAME':<35} | {'LLM?':^5} | {'MOCK':^8} | {'GROQ':^8} | {'DELTA':^8}"
    print(header)
    print("─" * 90)

    mock_pass = groq_pass = 0
    total = len(all_ids)

    for cid in all_ids:
        m = mock_map.get(cid)
        g = groq_map.get(cid)
        name = (m or g or {}).get("name", cid)[:35]
        is_llm = "LLM" if cid in llm_cases else "det"

        mock_status = ("✓" if m.get("passed") else "✗") if m else "—"
        groq_status = ("✓" if g.get("passed") else "✗") if g else "—"

        if m and m.get("passed"):
            mock_pass += 1
        if g and g.get("passed"):
            groq_pass += 1

        delta = ""
        if m and g:
            if m.get("passed") and g.get("passed"):
                delta = "="
            elif m.get("passed") and not g.get("passed"):
                delta = "▼ GROQ"
            elif not m.get("passed") and g.get("passed"):
                delta = "▲ GROQ"
            else:
                delta = "both fail"

        print(f"  {cid:<8} | {name:<35} | {is_llm:^5} | {'PASS' if mock_status=='✓' else ('FAIL' if mock_status=='✗' else '—'):^8} | {'PASS' if groq_status=='✓' else ('FAIL' if groq_status=='✗' else '—'):^8} | {delta:^8}")

    print("─" * 90)
    mock_rate = f"{mock_pass}/{total} ({mock_pass/total*100:.1f}%)" if total else "N/A"
    groq_rate = f"{groq_pass}/{total} ({groq_pass/total*100:.1f}%)" if total else "N/A"
    print(f"  TOTAL : Mock={mock_rate}   Groq={groq_rate}")

    if groq.get("avg_llm_latency_s"):
        print(f"  Groq avg LLM latency: {groq['avg_llm_latency_s']}s | "
              f"Retries: {groq.get('total_retries', 0)} | "
              f"Validation failures: {groq.get('validation_failures', 0)}")

    print("═" * 90)
    print()
    print("  Interpretation")
    print("  ─────────────")
    print("  det  cases are deterministic — results should be identical across providers.")
    print("  LLM  cases are probabilistic — Groq results may vary between runs.")
    print("  Mock 10/10 baseline is the regression target.")
    if groq:
        note = "Groq results are observed, not guaranteed — LLM output is probabilistic."
        if groq_pass < total:
            failed = [cid for cid in all_ids if groq_map.get(cid) and not groq_map[cid].get("passed")]
            note += f" Failed cases: {failed}."
        print(f"  {note}")
    print("═" * 90 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Mock vs Groq evaluation results.")
    parser.add_argument("--mock", default="eval/results_mock.json")
    parser.add_argument("--groq", default="eval/results_groq.json")
    args = parser.parse_args()
    compare(args.mock, args.groq)

"""
scripts/evaluate.py
-------------------
Standalone evaluation runner for Phase 7.

Loads all test traces, runs the full conversation pipeline against each,
and prints a comprehensive Recall@10 report with:

  - Per-trace results (recall, hits, rec names)
  - Aggregate statistics (mean, std, min, max)
  - Hallucination count
  - Pass/fail summary

Usage:
    python scripts/evaluate.py
    python scripts/evaluate.py --traces data/test_traces.json
    python scripts/evaluate.py --url http://localhost:8000  # against running server
    python scripts/evaluate.py --dev                         # dev traces only (1-8)
    python scripts/evaluate.py --holdout                     # holdout only (9-10)

Exit code:
    0  — all checks pass (mean recall ≥ 0.50, 0 hallucinations, 0 schema errors)
    1  — one or more checks failed
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RECALL_TARGET = 0.50          # Mean Recall@10 must be ≥ this
VARIANCE_THRESHOLD = 0.30     # Std dev must be < this (overfitting guard)
DEFAULT_TRACES = Path("data/test_traces.json")


# ---------------------------------------------------------------------------
# API client (either TestClient or real HTTP)
# ---------------------------------------------------------------------------

def make_client(base_url: Optional[str] = None):
    """Return a callable client(messages) → response dict."""
    if base_url:
        def http_client(messages):
            resp = requests.post(
                f"{base_url.rstrip('/')}/chat",
                json={"messages": messages},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        return http_client
    else:
        from main import app
        tc = TestClient(app)
        def test_client(messages):
            resp = tc.post("/chat", json={"messages": messages})
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json()
        return test_client


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def recall_at_10(rec_names: List[str], expected: List[str]) -> float:
    if not expected:
        return 1.0
    return len(set(rec_names) & set(expected)) / len(expected)


def run_trace(
    trace: Dict,
    client_fn,
    catalog_verify=None,
) -> Dict:
    """
    Run a single trace and return a result dict with:
        trace_id, persona, recall, hits, recs, expected,
        hallucinations, schema_ok, is_comparison
    """
    conv = trace["conversation"]
    expected = trace.get("expected_shortlist", [])
    is_comparison = trace.get("is_comparison", False)
    result = {
        "trace_id": trace["trace_id"],
        "persona": trace["persona"],
        "is_comparison": is_comparison,
        "expected": expected,
        "recs": [],
        "recall": None,
        "hits": 0,
        "hallucinations": 0,
        "schema_ok": True,
        "error": None,
    }

    try:
        data = client_fn(conv)

        # Schema check
        for field in ("reply", "recommendations", "end_of_conversation"):
            if field not in data:
                result["schema_ok"] = False
                result["error"] = f"Missing field: {field}"
                return result

        recs = data["recommendations"]
        rec_names_list = [r.get("name", "") for r in recs]
        result["recs"] = rec_names_list

        # URL validation / hallucination check
        if catalog_verify:
            for rec in recs:
                if not catalog_verify(rec.get("url", "")):
                    result["hallucinations"] += 1

        # Recall
        if not is_comparison and expected:
            r = recall_at_10(rec_names_list, expected)
            result["recall"] = r
            result["hits"] = len(set(rec_names_list) & set(expected))

        # Comparison-specific check
        if is_comparison and recs:
            result["error"] = f"Comparison trace returned unexpected recs: {rec_names_list}"

    except Exception as exc:
        result["schema_ok"] = False
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(results: List[Dict], show_all: bool = True) -> bool:
    """Print evaluation report and return True if all checks pass."""
    print("\n" + "=" * 80)
    print("  SHL RECOMMENDER — PHASE 7 EVALUATION REPORT")
    print("=" * 80)

    recalls = [r["recall"] for r in results if r["recall"] is not None]
    total_hallucinations = sum(r["hallucinations"] for r in results)
    schema_failures = [r for r in results if not r["schema_ok"]]

    # Per-trace table
    print(f"\n{'TRACE':<12} {'PERSONA':<38} {'RECALL':>7}  {'HITS':<8} RECS")
    print("-" * 80)
    for r in results:
        if r["is_comparison"]:
            label = "COMPARE"
            recall_str = "  N/A  "
        elif r["recall"] is not None:
            label = f"{r['recall']:.0%}"
            recall_str = f"  {label:>5}  "
        else:
            label = "—"
            recall_str = "  N/A  "

        hits_str = f"{r['hits']}/{len(r['expected'])}" if r["expected"] else "—"
        rec_preview = ", ".join(r["recs"][:3])
        if len(r["recs"]) > 3:
            rec_preview += f" (+{len(r['recs'])-3})"

        status = "✓" if r["schema_ok"] and r["hallucinations"] == 0 else "✗"
        print(
            f"  {r['trace_id']:<10} {r['persona']:<38} "
            f"{recall_str} {hits_str:<8} {rec_preview}"
        )
        if r["error"]:
            print(f"    ⚠ {r['error']}")

    print("-" * 80)

    # Aggregate
    print("\n  AGGREGATE STATISTICS")
    print(f"  {'Evaluable traces':<30}: {len(recalls)}")
    if recalls:
        mean_r = statistics.mean(recalls)
        std_r = statistics.pstdev(recalls) if len(recalls) > 1 else 0.0
        min_r = min(recalls)
        max_r = max(recalls)
        print(f"  {'Mean Recall@10':<30}: {mean_r:.2%}")
        print(f"  {'Std Dev Recall@10':<30}: {std_r:.3f}")
        print(f"  {'Min Recall@10':<30}: {min_r:.2%}")
        print(f"  {'Max Recall@10':<30}: {max_r:.2%}")
    print(f"  {'Total hallucinations':<30}: {total_hallucinations}")
    print(f"  {'Schema failures':<30}: {len(schema_failures)}")

    # Pass/fail summary
    print("\n  PASS / FAIL")
    checks = []

    if recalls:
        mean_r = statistics.mean(recalls)
        std_r = statistics.pstdev(recalls) if len(recalls) > 1 else 0.0
        recall_ok = mean_r >= RECALL_TARGET
        variance_ok = std_r < VARIANCE_THRESHOLD
        checks.append(("Mean Recall@10 >= 50%", recall_ok, f"{mean_r:.2%}"))
        checks.append(("Recall variance < 0.30 (no overfitting)", variance_ok, f"{std_r:.3f}"))

    checks.append(("Zero hallucinations", total_hallucinations == 0, str(total_hallucinations)))
    checks.append(("Zero schema failures", len(schema_failures) == 0, str(len(schema_failures))))

    all_pass = True
    for label, passed, value in checks:
        icon = "PASS" if passed else "FAIL"
        print(f"  {icon} {label:<44} ({value})")
        if not passed:
            all_pass = False

    print("\n  " + ("ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED"))
    print("=" * 80 + "\n")
    return all_pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Phase 7 evaluation runner")
    parser.add_argument(
        "--traces", default=str(DEFAULT_TRACES), help="Path to test_traces.json"
    )
    parser.add_argument(
        "--url", default=None,
        help="Base URL of a running server (default: use TestClient)"
    )
    parser.add_argument(
        "--dev", action="store_true", help="Only evaluate traces 1-8 (dev set)"
    )
    parser.add_argument(
        "--holdout", action="store_true", help="Only evaluate traces 9-10 (holdout)"
    )
    args = parser.parse_args()

    # Load traces
    traces_path = Path(args.traces)
    if not traces_path.exists():
        print(f"ERROR: Traces file not found: {traces_path}", file=sys.stderr)
        sys.exit(1)

    with open(traces_path, "r", encoding="utf-8") as fh:
        all_traces = json.load(fh)

    # Apply split
    if args.dev:
        traces = all_traces[:-2]
        print(f"[DEV] Evaluating traces 1-{len(traces)}")
    elif args.holdout:
        traces = all_traces[-2:]
        print(f"[HOLDOUT] Evaluating last 2 traces")
    else:
        traces = all_traces
        print(f"Evaluating all {len(traces)} traces")

    # Build client
    client_fn = make_client(args.url)

    # Get catalog verifier if available
    catalog_verify = None
    if not args.url:
        try:
            from src.api.endpoints import get_catalog_manager
            cat = get_catalog_manager()
            catalog_verify = cat.verify_url
        except Exception as e:
            print(f"[WARN] Could not load catalog verifier: {e}")

    # Run evaluation
    print("Running traces...", flush=True)
    results = []
    for i, trace in enumerate(traces, 1):
        print(f"  [{i}/{len(traces)}] {trace['trace_id']} — {trace['persona']}", end=" ", flush=True)
        result = run_trace(trace, client_fn, catalog_verify=catalog_verify)
        recall_str = f"Recall={result['recall']:.0%}" if result["recall"] is not None else "N/A"
        print(f"({recall_str})")
        results.append(result)

    # Print report
    all_pass = print_report(results)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()

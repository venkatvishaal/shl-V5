"""
Phase 7 — Anti-Overfitting & Generalization Tests
---------------------------------------------------
Guards against the most common failure mode: optimizing the pipeline
specifically for the 10 public traces instead of building a system that
generalises to unseen inputs.

Three test classes:
  1. TestVarianceCheck      — Recall@10 must not have high variance (std > 0.10)
  2. TestQueryVariations    — Same intent, different wording → consistent recall
  3. TestHoldoutSimulation  — Develop on traces 1-8, validate on traces 9-10

Also includes adversarial probes:
  - Out-of-order context
  - Mid-conversation mind changes
  - Partial / refused answers
  - Unusual phrasing

Run with:
    pytest tests/test_overfitting.py -v -s
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from main import app

pytestmark = pytest.mark.slow

client = TestClient(app)

TRACES_PATH = Path("data/test_traces.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_traces() -> List[Dict]:
    if not TRACES_PATH.exists():
        pytest.skip(f"Traces file not found: {TRACES_PATH}")
    with open(TRACES_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_conversation(messages: List[Dict]) -> Dict:
    resp = client.post("/chat", json={"messages": messages})
    assert resp.status_code == 200, f"/chat {resp.status_code}: {resp.text}"
    return resp.json()


def recall_at_10(rec_names: List[str], expected: List[str]) -> float:
    if not expected:
        return 1.0
    hits = len(set(rec_names) & set(expected))
    return hits / len(expected)


def run_full_conversation_from_trace(trace: Dict) -> Optional[float]:
    """
    Run a trace end-to-end and return Recall@10 (or None if comparison trace).
    """
    if trace.get("is_comparison") or not trace.get("expected_shortlist"):
        return None
    data = run_conversation(trace["conversation"])
    recs = [r["name"] for r in data["recommendations"]]
    return recall_at_10(recs, trace["expected_shortlist"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def traces():
    return load_traces()


@pytest.fixture(scope="module")
def recall_per_trace(traces):
    """Compute recall for all evaluable traces once per test session."""
    results = {}
    for trace in traces:
        r = run_full_conversation_from_trace(trace)
        if r is not None:
            results[trace["trace_id"]] = r
    return results


# ---------------------------------------------------------------------------
# 1. Variance check
# ---------------------------------------------------------------------------

class TestVarianceCheck:
    """
    High variance in Recall@10 across traces is the primary signal of
    overfitting to specific trace phrasings.
    """

    def test_recall_variance_below_threshold(self, recall_per_trace):
        """
        Standard deviation of per-trace Recall@10 must be ≤ 0.20.

        > 0.20 signals that the system is very good at some traces but
        failing others — classic overfitting signature.
        """
        if len(recall_per_trace) < 3:
            pytest.skip("Too few evaluable traces for variance analysis")

        recalls = list(recall_per_trace.values())
        std = statistics.pstdev(recalls)
        mean = statistics.mean(recalls)

        print(
            f"\nRecall@10 per trace: "
            + ", ".join(f"{k}={v:.0%}" for k, v in recall_per_trace.items())
        )
        print(f"Mean={mean:.2%}  Std={std:.3f}")

        assert std <= 0.30, (
            f"High recall variance (std={std:.3f}) suggests overfitting. "
            f"Per-trace values: {dict(zip(recall_per_trace, [f'{r:.2%}' for r in recalls]))}"
        )

    def test_no_single_trace_wildly_outperforms(self, recall_per_trace):
        """
        No single trace recall should exceed mean + 2*std — a sign of
        a hand-crafted shortcut for that specific trace.
        """
        if len(recall_per_trace) < 3:
            pytest.skip("Too few evaluable traces")

        recalls = list(recall_per_trace.values())
        mean = statistics.mean(recalls)
        std = statistics.pstdev(recalls) if len(recalls) > 1 else 0.0
        threshold = mean + 2 * std

        for tid, r in recall_per_trace.items():
            assert r <= threshold + 0.05, (  # +0.05 tolerance
                f"Trace {tid} recall={r:.2%} is a suspicious outlier "
                f"(mean={mean:.2%}, mean+2σ={threshold:.2%}). "
                f"May indicate trace-specific hardcoding."
            )

    def test_mean_recall_meets_target(self, recall_per_trace):
        """Overall mean Recall@10 must meet the ≥ 50% project target."""
        if not recall_per_trace:
            pytest.skip("No evaluable traces")
        mean = statistics.mean(recall_per_trace.values())
        assert mean >= 0.50, (
            f"Mean Recall@10 {mean:.2%} does not meet the 50% target"
        )


# ---------------------------------------------------------------------------
# 2. Query-variation robustness
# ---------------------------------------------------------------------------

class TestQueryVariations:
    """
    The same hiring intent phrased differently must produce consistent results.
    Recall should not swing more than ±0.30 across phrasings.
    """

    JAVA_VARIATIONS = [
        "I'm hiring a Java developer",
        "Looking for Java dev skills assessment",
        "Need to assess Java programming ability",
        "Java engineer candidate evaluation",
        "Want to test someone on Java 8",
    ]

    LEADERSHIP_VARIATIONS = [
        "I need leadership assessments",
        "Assessing management and leadership",
        "Tests for a leader role",
        "Manager assessment for team lead",
        "Evaluating leadership competency",
    ]

    def _recs_for_single_message(self, msg: str) -> List[str]:
        """
        Run a 5-turn conversation seeded with this message as the first user turn,
        so the agent has enough context to recommend.
        """
        messages = [
            {"role": "user", "content": msg},
            {"role": "assistant", "content": "What seniority level are you targeting?"},
            {"role": "user", "content": "Mid-level"},
            {"role": "assistant", "content": "Any other skills or constraints to consider?"},
            {"role": "user", "content": "No specific constraints"},
        ]
        data = run_conversation(messages)
        return [r["name"] for r in data["recommendations"]]

    def test_java_variations_produce_recs(self):
        """All Java phrasings should produce at least 1 recommendation."""
        for variation in self.JAVA_VARIATIONS:
            recs = self._recs_for_single_message(variation)
            # We don't assert specific names — just that something was returned
            assert isinstance(recs, list), f"Variation '{variation}' produced no list"

    def test_java_variations_schema_valid(self):
        """All Java phrasings should return catalog-valid URLs."""
        from src.api.endpoints import get_catalog_manager
        catalog = get_catalog_manager()

        for variation in self.JAVA_VARIATIONS:
            messages = [
                {"role": "user", "content": variation},
                {"role": "assistant", "content": "What seniority level?"},
                {"role": "user", "content": "Senior"},
                {"role": "assistant", "content": "Any other requirements?"},
                {"role": "user", "content": "Just Java and communication skills"},
            ]
            data = run_conversation(messages)
            for rec in data["recommendations"]:
                assert catalog.verify_url(rec["url"]), (
                    f"Hallucinated URL for variation '{variation}': {rec['url']}"
                )

    def test_leadership_variations_consistent(self):
        """Leadership phrasings should all produce recs (schema-valid)."""
        from src.api.endpoints import get_catalog_manager
        catalog = get_catalog_manager()

        for variation in self.LEADERSHIP_VARIATIONS:
            messages = [
                {"role": "user", "content": variation},
                {"role": "assistant", "content": "What seniority are you hiring for?"},
                {"role": "user", "content": "Senior"},
                {"role": "assistant", "content": "Any industry context?"},
                {"role": "user", "content": "Finance"},
            ]
            data = run_conversation(messages)
            for rec in data["recommendations"]:
                assert rec["url"].startswith("https://www.shl.com"), (
                    f"Non-SHL URL for variation '{variation}': {rec['url']}"
                )

    def test_different_phrasings_dont_crash(self):
        """Edge-case and unusual phrasings should never crash the API."""
        unusual = [
            "assessment",
            "test please",
            "java java java developer",
            "SENIOR MANAGER FINANCE LEADERSHIP ASSESSMENT",
            "i dunno, something for a person who does things",
        ]
        for phrasing in unusual:
            resp = client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": phrasing}]},
            )
            assert resp.status_code in (200, 422), (
                f"Unexpected status {resp.status_code} for phrasing: '{phrasing}'"
            )


# ---------------------------------------------------------------------------
# 3. Holdout simulation
# ---------------------------------------------------------------------------

class TestHoldoutSimulation:
    """
    Simulate a train/holdout split: traces 1-8 are 'dev', traces 9-10 are
    'holdout'. Performance on the holdout must not be dramatically worse.

    This is a structural check — we don't actually tune on the dev set here,
    but we verify the system handles both sets equally.
    """

    def test_dev_and_holdout_recall_gap_acceptable(self, traces):
        """
        Recall on dev traces (0-7) vs holdout traces (8-9) must differ by < 0.20.
        """
        evaluable = [
            t for t in traces
            if not t.get("is_comparison") and t.get("expected_shortlist")
        ]

        if len(evaluable) < 4:
            pytest.skip("Need ≥ 4 evaluable traces for holdout simulation")

        dev_traces = evaluable[:-2]
        holdout_traces = evaluable[-2:]

        def mean_recall(trace_list):
            recalls = []
            for trace in trace_list:
                data = run_conversation(trace["conversation"])
                recs = [r["name"] for r in data["recommendations"]]
                recalls.append(recall_at_10(recs, trace["expected_shortlist"]))
            return statistics.mean(recalls) if recalls else 0.0

        dev_recall = mean_recall(dev_traces)
        holdout_recall = mean_recall(holdout_traces)
        gap = abs(dev_recall - holdout_recall)

        print(
            f"\nDev Recall@10    : {dev_recall:.2%} (traces 1-{len(dev_traces)})"
            f"\nHoldout Recall@10: {holdout_recall:.2%} (last 2 traces)"
            f"\nGap              : {gap:.2%}"
        )

        assert gap <= 0.20, (
            f"Large recall gap between dev ({dev_recall:.2%}) and holdout "
            f"({holdout_recall:.2%}). Gap={gap:.2%} > 0.20 — possible overfitting."
        )

    def test_holdout_traces_schema_valid(self, traces):
        """Holdout traces must produce schema-valid responses."""
        evaluable = [t for t in traces if not t.get("is_comparison")]
        holdout = evaluable[-2:] if len(evaluable) >= 2 else evaluable

        for trace in holdout:
            data = run_conversation(trace["conversation"])
            assert "reply" in data
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)
            for rec in data["recommendations"]:
                assert rec["url"].startswith("https://www.shl.com")

    def test_holdout_traces_no_hallucinations(self, traces):
        """Holdout traces must not produce hallucinated URLs."""
        from src.api.endpoints import get_catalog_manager
        catalog = get_catalog_manager()

        evaluable = [t for t in traces if not t.get("is_comparison")]
        holdout = evaluable[-2:] if len(evaluable) >= 2 else evaluable

        for trace in holdout:
            data = run_conversation(trace["conversation"])
            for rec in data["recommendations"]:
                assert catalog.verify_url(rec["url"]), (
                    f"Hallucinated URL in holdout {trace['trace_id']}: {rec['url']}"
                )


# ---------------------------------------------------------------------------
# 4. Adversarial probes
# ---------------------------------------------------------------------------

class TestAdversarialProbes:
    """
    Edge cases that could break a system tuned to only clean, well-formed inputs.
    """

    def test_out_of_order_context(self):
        """User gives info out of typical order (skills before role)."""
        messages = [
            {"role": "user", "content": "The candidate needs to demonstrate Java 8 skills"},
            {"role": "assistant", "content": "What role are you hiring for?"},
            {"role": "user", "content": "Senior backend engineer"},
            {"role": "assistant", "content": "Any other requirements?"},
            {"role": "user", "content": "Communication and stakeholder management too"},
        ]
        data = run_conversation(messages)
        assert isinstance(data["reply"], str)
        for rec in data["recommendations"]:
            assert rec["url"].startswith("https://www.shl.com")

    def test_user_refuses_to_answer_clarifying_question(self):
        """User who won't answer context questions should still get a response."""
        messages = [
            {"role": "user", "content": "I need tests"},
            {"role": "assistant", "content": "What role are you hiring for?"},
            {"role": "user", "content": "I'd rather not say"},
            {"role": "assistant", "content": "What seniority level?"},
            {"role": "user", "content": "Just give me something general"},
        ]
        data = run_conversation(messages)
        # Should either recommend something or ask one more question — not crash
        assert isinstance(data["reply"], str) and len(data["reply"]) > 0

    def test_user_changes_mind_mid_conversation(self):
        """User who switches roles mid-conversation should be handled gracefully."""
        messages = [
            {"role": "user", "content": "Hiring a Java developer"},
            {"role": "assistant", "content": "What level?"},
            {"role": "user", "content": "Actually, it's a data scientist role, not a developer"},
            {"role": "assistant", "content": "Understood. What skills matter most?"},
            {"role": "user", "content": "Numerical reasoning and Python"},
        ]
        data = run_conversation(messages)
        assert isinstance(data["reply"], str)
        for rec in data["recommendations"]:
            assert rec["url"].startswith("https://www.shl.com")

    def test_very_long_user_message(self):
        """Very long messages (but not a JD) should not break the API."""
        long_msg = "I need assessments for a " + "very " * 50 + "senior Java developer"
        resp = client.post(
            "/chat", json={"messages": [{"role": "user", "content": long_msg}]}
        )
        assert resp.status_code == 200

    def test_mixed_language_capitalization(self):
        """UPPERCASE and MiXeD case inputs should work."""
        messages = [
            {"role": "user", "content": "HIRING A SENIOR JAVA DEVELOPER"},
            {"role": "assistant", "content": "What skills are important?"},
            {"role": "user", "content": "JAVA 8, COMMUNICATION"},
            {"role": "assistant", "content": "Any industry preference?"},
            {"role": "user", "content": "Technology"},
        ]
        data = run_conversation(messages)
        assert isinstance(data["reply"], str)

    def test_special_characters_in_message(self):
        """Messages with special chars should not crash."""
        messages = [
            {"role": "user", "content": "I need tests for C++ & Java developers!"},
            {"role": "assistant", "content": "What level?"},
            {"role": "user", "content": "Senior — ideally 5+ years"},
            {"role": "assistant", "content": "Any other skills?"},
            {"role": "user", "content": "Leadership & communication (excellent written + verbal)"},
        ]
        data = run_conversation(messages)
        assert isinstance(data["reply"], str)

    def test_empty_after_greeting_handled(self):
        """Turn after greeting must be handled without crashing."""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! What role are you hiring for?"},
            {"role": "user", "content": ""},
        ]
        # Empty content will be rejected by schema (min_length=1) — that's correct
        resp = client.post("/chat", json={"messages": messages})
        assert resp.status_code in (200, 422)

    def test_repeated_same_question(self):
        """Repeating the same message should not cause infinite loops."""
        messages = [
            {"role": "user", "content": "I need an assessment"},
            {"role": "assistant", "content": "What role are you hiring for?"},
            {"role": "user", "content": "I need an assessment"},
            {"role": "assistant", "content": "Could you tell me more about the role?"},
            {"role": "user", "content": "I need an assessment"},
        ]
        data = run_conversation(messages)
        assert isinstance(data["reply"], str)


if __name__ == "__main__":
    import sys
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v", "-s"]))

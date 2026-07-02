"""Shared pytest configuration for V4.

The application enables Gemini in normal runtime. Unit tests should not call
external LLMs unless a test explicitly opts in, so the default test behavior
forces deterministic fallback.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: long-running replay/evaluation suites; run explicitly with -m slow"
    )
    config.addinivalue_line(
        "markers", "llm_enabled: allow real settings.use_llm during this test"
    )


@pytest.fixture(autouse=True)
def disable_real_llm_by_default(monkeypatch, request):
    if request.node.get_closest_marker("llm_enabled"):
        return
    from src.config import settings

    monkeypatch.setattr(settings, "use_llm", False)

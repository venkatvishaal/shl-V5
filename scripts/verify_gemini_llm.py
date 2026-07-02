"""Verify that the Gemini-backed /chat path is enabled and timeout-safe.

This script intentionally does not print API keys. It exercises the FastAPI app
through TestClient and validates schema/catalog grounding plus elapsed time.
"""

from __future__ import annotations

import sys
import time
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from src.api.endpoints import get_catalog_manager  # noqa: E402
from src.config import settings  # noqa: E402
from src.llm.client import LLMClient  # noqa: E402


def main() -> int:
    if not settings.use_llm:
        print("FAIL: USE_LLM is not enabled")
        return 1
    if settings.llm_provider.lower() != "gemini":
        print(f"FAIL: LLM_PROVIDER is {settings.llm_provider!r}, expected 'gemini'")
        return 1
    if not settings.gemini_api_key:
        print("FAIL: GEMINI_API_KEY is not configured")
        return 1
    if settings.llm_timeout_seconds >= 30:
        print(f"FAIL: LLM_TIMEOUT_SECONDS must be < 30, got {settings.llm_timeout_seconds}")
        return 1

    direct_started = time.monotonic()
    try:
        direct_text = asyncio.run(
            asyncio.wait_for(
                LLMClient().generate(
                    "Reply with exactly: Gemini OK",
                    system_prompt="You are a concise health-check assistant.",
                ),
                timeout=settings.llm_timeout_seconds,
            )
        )
    except Exception as exc:
        print(f"FAIL: direct Gemini generation failed: {exc!r}")
        return 1
    direct_elapsed = time.monotonic() - direct_started
    if not direct_text.strip():
        print("FAIL: direct Gemini generation returned empty text")
        return 1

    client = TestClient(app)
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Hiring a mid-level Java developer who works with stakeholders. Recommend assessments.",
            }
        ]
    }

    started = time.monotonic()
    response = client.post("/chat", json=payload)
    elapsed = time.monotonic() - started

    if elapsed >= 30:
        print(f"FAIL: /chat took {elapsed:.2f}s, exceeding the 30s assignment cap")
        return 1
    if response.status_code != 200:
        print(f"FAIL: /chat returned {response.status_code}: {response.text}")
        return 1

    data = response.json()
    required_keys = {"reply", "recommendations", "end_of_conversation"}
    if set(data) != required_keys:
        print(f"FAIL: response keys are {sorted(data)}, expected {sorted(required_keys)}")
        return 1

    catalog = get_catalog_manager()
    for item in data["recommendations"]:
        if not catalog.verify_url(item.get("url", "")):
            print(f"FAIL: hallucinated/non-catalog URL: {item.get('url')}")
            return 1

    print("PASS: Gemini generation works; /chat returned valid schema under timeout")
    print(
        f"provider={settings.llm_provider}; model={settings.llm_model}; "
        f"gemini_elapsed={direct_elapsed:.2f}s; chat_elapsed={elapsed:.2f}s"
    )
    print(f"recommendations={len(data['recommendations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

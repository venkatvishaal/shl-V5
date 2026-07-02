"""LLM-specific safety tests without calling external providers."""

import asyncio
import time

import pytest

from src.agent.behavior_handler import BehaviorHandler
from src.api.endpoints import get_catalog_manager
from src.config import settings


class SlowLLM:
    async def generate(self, user_prompt: str, system_prompt: str | None = None) -> str:
        await asyncio.sleep(settings.llm_timeout_seconds + 0.2)
        return "This should not be used."


class HallucinatingLLM:
    async def generate(self, user_prompt: str, system_prompt: str | None = None) -> str:
        return """
        Here is a shortlist.
        ```json
        [
          {
            "name": "Invented SHL Test",
            "url": "https://www.shl.com/products/product-catalog/view/not-real/",
            "test_type": "K"
          }
        ]
        ```
        """


@pytest.mark.asyncio
async def test_llm_timeout_falls_back_under_budget(monkeypatch):
    monkeypatch.setattr(settings, "use_llm", True)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 0.05)
    handler = BehaviorHandler(get_catalog_manager())
    handler._llm = SlowLLM()

    started = time.monotonic()
    reply, recs, done = await handler.recommend("Hiring a Java developer", {
        "role": "Java Developer",
        "skills": ["java", "communication"],
        "seniority": "mid",
    })
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert reply
    assert 1 <= len(recs) <= 10
    assert done is True


@pytest.mark.asyncio
async def test_llm_hallucinated_urls_are_discarded(monkeypatch):
    monkeypatch.setattr(settings, "use_llm", True)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 1.0)
    catalog = get_catalog_manager()
    handler = BehaviorHandler(catalog)
    handler._llm = HallucinatingLLM()

    _, recs, _ = await handler.recommend("Hiring a Java developer", {
        "role": "Java Developer",
        "skills": ["java", "communication"],
        "seniority": "mid",
    })

    assert recs
    assert all(catalog.verify_url(item["url"]) for item in recs)
    assert all("not-real" not in item["url"] for item in recs)


@pytest.mark.llm_enabled
def test_llm_settings_are_gemini_and_timeout_safe():
    assert settings.use_llm is True
    assert settings.llm_provider.lower() == "gemini"
    assert settings.gemini_api_key
    assert settings.llm_timeout_seconds < 30

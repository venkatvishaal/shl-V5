"""
LLMClient
---------
Async wrapper around four LLM providers:
  - Anthropic Claude  (primary)
  - OpenAI            (fallback / alternative)
  - Google Gemini     (fallback / alternative)
  - Groq              (low-latency alternative)

Design decisions
~~~~~~~~~~~~~~~~
* Pure raw SDK — no LangChain/LlamaIndex.  Every call is explicit so
  hallucination guards in BehaviorHandler stay in full control.
* Async-first.  All provider calls run in an executor to keep the
  FastAPI event loop unblocked even though the underlying SDKs are sync.
* Retry with exponential back-off on transient errors (rate-limit, 5xx).
* Transparent fallback: if the primary provider fails after retries, the
  caller receives the exception; BehaviorHandler owns the fallback policy.

Usage
~~~~~
    from src.llm.client import LLMClient

    client = LLMClient()
    reply  = await client.generate(user_prompt, system_prompt=system_prompt)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retry config
# ---------------------------------------------------------------------------

_MAX_RETRIES = 1
_BASE_DELAY  = 1.0   # seconds; doubles each attempt
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    """Heuristic: retry on rate-limit / server errors, not on auth/bad-request."""
    msg = str(exc).lower()
    retryable_keywords = (
        "rate limit", "rate_limit", "429", "500", "502", "503", "504",
        "timeout", "connection", "overloaded",
    )
    return any(kw in msg for kw in retryable_keywords)


async def _with_retries(coro_fn, *args, max_retries: int = _MAX_RETRIES, **kwargs):
    """Run a coroutine-producing callable with a small timeout-safe retry budget."""
    delay = _BASE_DELAY
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == max_retries:
                raise
            logger.warning(
                f"LLM call failed (attempt {attempt}/{max_retries}): {exc!r}. "
                f"Retrying in {delay:.1f}s …"
            )
            await asyncio.sleep(delay)
            delay *= 2

    raise last_exc  # unreachable, but satisfies type checkers


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Provider-agnostic async LLM client.

    Provider is selected from settings.llm_provider:
        "anthropic" | "openai" | "gemini" | "groq"

    All methods raise on unrecoverable failure so callers can implement
    their own fallback policy.
    """

    def __init__(self):
        self.provider    = settings.llm_provider.lower()
        self.model       = settings.llm_model
        self.max_tokens  = settings.llm_max_tokens
        self.temperature = settings.llm_temperature
        logger.info(
            f"LLMClient initialised — provider={self.provider}, model={self.model}"
        )

    # ── Public API ──────────────────────────────────────────────────────

    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a completion.

        Args:
            user_prompt:   The user-turn prompt (task instructions + data).
            system_prompt: Behavioural instructions for the LLM.
                           If None, the default SHL-specialist system prompt
                           from prompts.py is used.

        Returns:
            The generated text string.

        Raises:
            RuntimeError: If the configured provider is unknown.
            Exception:    Any provider SDK exception after retries exhausted.
        """
        if system_prompt is None:
            from src.llm.prompts import DEFAULT_SYSTEM_PROMPT
            system_prompt = DEFAULT_SYSTEM_PROMPT

        dispatch = {
            "anthropic": self._generate_anthropic,
            "openai":    self._generate_openai,
            "gemini":    self._generate_gemini,
            "groq":      self._generate_groq,
        }

        fn = dispatch.get(self.provider)
        if fn is None:
            raise RuntimeError(
                f"Unknown LLM provider: '{self.provider}'. "
                f"Choose one of: {list(dispatch)}"
            )

        t0 = time.monotonic()
        max_retries = 1 if self.provider == "gemini" else 2
        result = await _with_retries(
            fn,
            user_prompt,
            system_prompt,
            max_retries=max_retries,
        )
        elapsed = time.monotonic() - t0
        logger.debug(
            f"LLM [{self.provider}] completed in {elapsed:.2f}s "
            f"({len(result)} chars)"
        )
        return result

    # ── Provider implementations ────────────────────────────────────────
    # Each runs the synchronous SDK call in a thread-pool executor to
    # avoid blocking the event loop.

    async def _generate_anthropic(
        self, user_prompt: str, system_prompt: str
    ) -> str:
        """Anthropic Claude — uses messages API."""
        if not settings.anthropic_api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or environment."
            )

        def _sync_call() -> str:
            from anthropic import Anthropic

            client = Anthropic(api_key=settings.anthropic_api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            # Claude returns a list of content blocks; first is always text
            return message.content[0].text

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_call)

    async def _generate_openai(
        self, user_prompt: str, system_prompt: str
    ) -> str:
        """OpenAI / compatible endpoint — chat completions API."""
        if not settings.openai_api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or environment."
            )

        def _sync_call() -> str:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_call)

    async def _generate_gemini(
        self, user_prompt: str, system_prompt: str
    ) -> str:
        """Google Gemini — generative AI SDK."""
        if not settings.gemini_api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or environment."
            )

        def _sync_call() -> str:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)

            generation_config = genai.types.GenerationConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            def _generate(model, prompt: str):
                try:
                    return model.generate_content(
                        prompt,
                        request_options={"timeout": settings.llm_timeout_seconds},
                    )
                except (TypeError, ValueError):
                    # Older google-generativeai versions may not support
                    # request_options. The outer BehaviorHandler wait_for still
                    # enforces the API budget and falls back safely.
                    return model.generate_content(prompt)

            try:
                model = genai.GenerativeModel(
                    model_name=self.model,
                    system_instruction=system_prompt,
                    generation_config=generation_config,
                )
                response = _generate(model, user_prompt)
            except TypeError:
                # Older SDK versions don't support system_instruction;
                # fall back to prepending it to the user prompt.
                model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=generation_config,
                )
                response = _generate(model, system_prompt + "\n\n" + user_prompt)
            # Handle both single-part and multi-part responses
            try:
                return response.text
            except ValueError:
                # Multi-part response (e.g. thinking models) — return the last part as the final answer
                if response.parts:
                    last_part = response.parts[-1]
                    if hasattr(last_part, "text") and last_part.text:
                        return last_part.text
                return "".join(part.text for part in response.parts if hasattr(part, "text") and part.text)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_call)

    async def _generate_groq(
        self, user_prompt: str, system_prompt: str
    ) -> str:
        """Groq — OpenAI-compatible chat completions."""
        if not settings.groq_api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. "
                "Add it to your .env file or environment."
            )

        def _sync_call() -> str:
            from groq import Groq

            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_call)

    # ── Utility ─────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        """
        Return True if the active provider has an API key set.
        Useful for health checks and test gates.
        """
        key_map = {
            "anthropic": settings.anthropic_api_key,
            "openai":    settings.openai_api_key,
            "gemini":    settings.gemini_api_key,
            "groq":      settings.groq_api_key,
        }
        return bool(key_map.get(self.provider))

"""LLM factory helper.

Provides a simple interface to create LLM clients for use in nodes.
Students should use this helper so the lab works with any supported provider.

Usage in nodes:
    from .llm import get_llm
    llm = get_llm()
    response = llm.invoke("Hello")
"""

from __future__ import annotations

import os


from typing import Any


def _llm_timeout_seconds() -> float:
    return float(os.getenv("LLM_TIMEOUT_SECONDS", "10"))


def _llm_max_retries() -> int:
    return int(os.getenv("LLM_MAX_RETRIES", "0"))

def get_llm(model: str | None = None, temperature: float = 0.0) -> Any:
    """Create an LLM client from environment configuration.

    Checks for API keys in this order:
    1. GEMINI_API_KEY → ChatGoogleGenerativeAI
    2. OPENAI_API_KEY → ChatOpenAI
    3. ANTHROPIC_API_KEY → ChatAnthropic

    Override model with the `model` parameter or LLM_MODEL env var.
    """
    if os.getenv("GEMINI_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import-untyped, import-not-found]
        except ImportError as exc:
            raise RuntimeError("Install: pip install langchain-google-genai") from exc
        return ChatGoogleGenerativeAI(
            model=str(model or os.getenv("LLM_MODEL", "gemini-2.5-flash")),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature,
            timeout=_llm_timeout_seconds(),
            max_retries=_llm_max_retries(),
        )

    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("Install: pip install langchain-openai") from exc
        return ChatOpenAI(
            model=str(model or os.getenv("LLM_MODEL", "gpt-4o-mini")),
            temperature=temperature,
            timeout=_llm_timeout_seconds(),
            max_retries=_llm_max_retries(),
        )

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from langchain_anthropic import ChatAnthropic  # type: ignore[import-untyped, import-not-found]
        except ImportError as exc:
            raise RuntimeError("Install: pip install langchain-anthropic") from exc
        return ChatAnthropic(
            model=str(model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")),
            temperature=temperature,
            timeout=_llm_timeout_seconds(),
            max_retries=_llm_max_retries(),
        )

    if os.getenv("MISTRAL_API_KEY"):
        try:
            from langchain_mistralai import ChatMistralAI
        except ImportError as exc:
            raise RuntimeError("Install: pip install langchain-mistralai") from exc
        return ChatMistralAI(
            model=str(model or os.getenv("LLM_MODEL", "mistral-large-latest")),  # type: ignore[call-arg]
            temperature=temperature,
            timeout=int(_llm_timeout_seconds()),
            max_retries=_llm_max_retries(),
        )

    raise RuntimeError(
        "No LLM API key found. Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env\n"
        "See .env.example for configuration."
    )

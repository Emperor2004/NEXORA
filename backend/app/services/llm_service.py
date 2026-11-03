import json
import logging
import os
from pathlib import Path

import ollama
from dotenv import load_dotenv
from app.services.model_trace import record_model_call, record_prompt

# Load backend/.env regardless of the current working directory.
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger("nexora.llm")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

PRIMARY_PROVIDER = os.getenv(
    "LLM_PRIMARY_PROVIDER", "ollama"
).lower()

FALLBACK_PROVIDER = os.getenv(
    "LLM_FALLBACK_PROVIDER", "gemini"
).lower()


def _generate_with_ollama(
    system_prompt: str,
    user_prompt: str,
    output_schema: dict,
    timeout_seconds: int | None = None,
    max_output_tokens: int | None = None,
) -> dict:

    options = {"temperature": 0, "num_ctx": 4096}
    if max_output_tokens is not None:
        options["num_predict"] = max_output_tokens
    client = ollama.Client(timeout=timeout_seconds) if timeout_seconds else None
    chat = client.chat if client else ollama.chat
    response = chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        format=output_schema,
        options=options,
        keep_alive="5m"
    )
    record_model_call("ollama", OLLAMA_MODEL)

    content = response.message.content

    if not content:
        raise RuntimeError("Ollama returned an empty response")

    return json.loads(content)


def _generate_with_gemini(
    system_prompt: str,
    user_prompt: str,
    output_schema: dict,
    timeout_seconds: int | None = None,
    max_output_tokens: int | None = None,
) -> dict:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    from google import genai
    from google.genai import types

    client_options = {"api_key": api_key}
    if timeout_seconds:
        client_options["http_options"] = types.HttpOptions(
            timeout=timeout_seconds * 1000
        )
    client = genai.Client(**client_options)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=output_schema,
            temperature=0,
            **({"max_output_tokens": max_output_tokens}
               if max_output_tokens is not None else {}),
        )
    )
    record_model_call("gemini", GEMINI_MODEL)

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    return json.loads(response.text)


PROVIDERS = {
    "ollama": _generate_with_ollama,
    "gemini": _generate_with_gemini
}


def generate_structured_output(
    system_prompt: str,
    user_prompt: str,
    output_schema: dict,
    provider: str | None = None,
    timeout_seconds: int | None = None,
    max_output_tokens: int | None = None,
    allowed_providers: tuple[str, ...] | list[str] | None = None,
) -> dict:

    record_prompt(system_prompt)

    provider_options = {}
    if timeout_seconds is not None:
        provider_options["timeout_seconds"] = timeout_seconds
    if max_output_tokens is not None:
        provider_options["max_output_tokens"] = max_output_tokens

    def call_provider(name):
        return PROVIDERS[name](
            system_prompt, user_prompt, output_schema, **provider_options
        )

    # Explicit provider selection is useful for testing.
    if provider is not None:

        selected = provider.lower()

        if selected not in PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {selected}")
        if allowed_providers is not None and selected not in allowed_providers:
            raise ValueError(f"Provider '{selected}' is not allowed for this agent")

        return call_provider(selected)

    allowed = tuple(allowed_providers) if allowed_providers is not None else tuple(PROVIDERS)
    if not allowed or any(name not in PROVIDERS for name in allowed):
        raise ValueError("Allowed provider policy is empty or contains an unsupported provider")
    primary = PRIMARY_PROVIDER if PRIMARY_PROVIDER in allowed else allowed[0]
    fallback = FALLBACK_PROVIDER if FALLBACK_PROVIDER in allowed else primary

    if primary not in PROVIDERS:
        raise ValueError(f"Unsupported primary provider: {primary}")

    if fallback not in PROVIDERS:
        raise ValueError(f"Unsupported fallback provider: {fallback}")

    try:
        logger.info("Using primary LLM provider: %s", primary)

        return call_provider(primary)

    except Exception as primary_error:

        logger.warning(
            "Primary provider '%s' failed. Switching to '%s'. Error: %s",
            primary,
            fallback,
            primary_error
        )

        if fallback == primary:
            raise RuntimeError(
                f"Primary provider failed: {primary_error}"
            ) from primary_error

        try:
            logger.info("Using fallback LLM provider: %s", fallback)

            return call_provider(fallback)

        except Exception as fallback_error:

            raise RuntimeError(
                "Both LLM providers failed. "
                f"Primary error: {primary_error}. "
                f"Fallback error: {fallback_error}"
            ) from fallback_error


def check_llm_connection():

    try:
        result = ollama.list()

        return {
            "connected": True,
            "model": OLLAMA_MODEL,
            "available_models": [
                model.model for model in result.models
            ],
            "primary_provider": PRIMARY_PROVIDER,
            "fallback_provider": FALLBACK_PROVIDER,
            "gemini_model": GEMINI_MODEL,
            "gemini_key_configured": bool(
                os.getenv("GEMINI_API_KEY")
            )
        }

    except Exception as error:

        return {
            "connected": False,
            "error": str(error),
            "primary_provider": PRIMARY_PROVIDER,
            "fallback_provider": FALLBACK_PROVIDER,
            "gemini_key_configured": bool(
                os.getenv("GEMINI_API_KEY")
            )
        }


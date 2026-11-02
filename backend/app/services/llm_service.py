import json
import logging
import os
from pathlib import Path

import ollama
from dotenv import load_dotenv

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
    output_schema: dict
) -> dict:

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        format=output_schema,
        options={
            "temperature": 0,
            "num_ctx": 4096
        },
        keep_alive="5m"
    )

    content = response.message.content

    if not content:
        raise RuntimeError("Ollama returned an empty response")

    return json.loads(content)


def _generate_with_gemini(
    system_prompt: str,
    user_prompt: str,
    output_schema: dict
) -> dict:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=output_schema,
            temperature=0
        )
    )

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
    provider: str | None = None
) -> dict:

    # Explicit provider selection is useful for testing.
    if provider is not None:

        selected = provider.lower()

        if selected not in PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {selected}")

        return PROVIDERS[selected](
            system_prompt,
            user_prompt,
            output_schema
        )

    primary = PRIMARY_PROVIDER
    fallback = FALLBACK_PROVIDER

    if primary not in PROVIDERS:
        raise ValueError(f"Unsupported primary provider: {primary}")

    if fallback not in PROVIDERS:
        raise ValueError(f"Unsupported fallback provider: {fallback}")

    try:
        logger.info("Using primary LLM provider: %s", primary)

        return PROVIDERS[primary](
            system_prompt,
            user_prompt,
            output_schema
        )

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

            return PROVIDERS[fallback](
                system_prompt,
                user_prompt,
                output_schema
            )

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


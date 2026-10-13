"""Gemini-backed advisor that narrates deterministic engine output.

Import of this module must never fail or require network access/API
keys - the client is created lazily on first use so the rest of the
app (and tests) can run without `GEMINI_API_KEY` configured.
"""

import logging
import os
import time
from typing import Any

from src.llm.customer_memory import get_customer_profile
from src.llm.prompts import build_grounded_prompt

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.8-flash"

# Transient-overload resilience: retry the primary model once with a short
# backoff, then fall back to these models in order if it's still failing
# (e.g. a 503 ServerError, or a 404/429 ClientError on a retired model or
# an exhausted per-model daily quota). gemini-3.5-flash-lite/gemini-3.5-
# flash are confirmed live and working (and on a separate quota bucket
# from the primary model) as of this writing; the remaining three are
# the specific candidates requested in the spec - each is tried once and
# we move on regardless of why it failed.
MAX_PRIMARY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 1.5
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.5-flash-lite",
]

# Load .env once at import time - NOT per-call inside _get_client(), since
# python-dotenv's load_dotenv() sets any var that is currently absent from
# os.environ, which would silently re-populate GEMINI_API_KEY from disk
# every time an advisor is used, defeating tests (and callers) that
# deliberately clear it via monkeypatch/os.environ for that call.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _clean_model_name(raw: str | None) -> str | None:
    """Strip surrounding whitespace/quotes a .env value might carry."""
    if raw is None:
        return None
    cleaned = raw.strip().strip("'\"").strip()
    return cleaned or None


class AdvisorConfigError(RuntimeError):
    """Raised when the advisor is used without a configured API key."""


class AdvisorAPIError(RuntimeError):
    """Raised when the Gemini API call fails."""


class GeminiAdvisor:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self._model = (
            _clean_model_name(model)
            or _clean_model_name(os.environ.get("GEMINI_MODEL"))
            or DEFAULT_MODEL
        )
        self._api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        api_key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise AdvisorConfigError(
                "GEMINI_API_KEY is not set. Add it to your .env file "
                "(see .env.example)."
            )

        from google import genai

        self._client = genai.Client(api_key=api_key)
        return self._client

    def _generate_with_retry(self, client: Any, prompt: str) -> Any:
        """Call generate_content, retrying transient 503s on the primary
        model with backoff before falling back to FALLBACK_MODELS in
        order. A non-transient error (e.g. a 404 on a retired model)
        skips straight to the next model rather than wasting a retry."""
        from google.genai import errors as genai_errors

        models_to_try = [self._model] + [
            m for m in FALLBACK_MODELS if m != self._model
        ]
        last_error: Exception | None = None
        # Every model's final error, not just the last one tried - a 429
        # on the primary model shouldn't be masked by a 404 on a
        # fallback. Callers inspect this to tell a real bug apart from
        # e.g. a quota exhaustion that happened to be followed by
        # fallbacks that are themselves unavailable for other reasons.
        per_model_errors: list[str] = []

        for model_index, model_name in enumerate(models_to_try):
            attempts = MAX_PRIMARY_ATTEMPTS if model_index == 0 else 1
            for attempt in range(attempts):
                try:
                    return client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                except genai_errors.ServerError as e:
                    last_error = e
                    logger.warning(
                        "Gemini model '%s' returned a transient server "
                        "error (attempt %d/%d): %s",
                        model_name,
                        attempt + 1,
                        attempts,
                        e,
                    )
                    if attempt < attempts - 1:
                        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    else:
                        per_model_errors.append(f"{model_name}: {type(e).__name__}: {e}")
                except Exception as e:  # noqa: BLE001 - any failure here just moves to the next model
                    last_error = e
                    logger.warning(
                        "Gemini model '%s' failed (%s); trying next "
                        "fallback if available.",
                        model_name,
                        type(e).__name__,
                    )
                    per_model_errors.append(f"{model_name}: {type(e).__name__}: {e}")
                    break

        raise AdvisorAPIError(
            f"Gemini API request failed on all models {models_to_try}: "
            + " | ".join(per_model_errors)
        ) from last_error

    def explain(
        self,
        computed_data: dict[str, Any],
        user_question: str,
        customer_memory: dict[str, Any] | None = None,
    ) -> str:
        """Return a grounded natural-language explanation of computed_data.

        `computed_data` must already contain every number referenced in
        the response - this method never computes anything itself.
        """
        # Automatically resolve customer profile if customer_id provided in data
        if customer_memory is None and isinstance(computed_data, dict):
            cust_id = computed_data.get("customer_id")
            if cust_id and isinstance(cust_id, str):
                customer_memory = get_customer_profile(cust_id)

        client = self._get_client()
        prompt = build_grounded_prompt(
            computed_data=computed_data,
            user_question=user_question,
            customer_memory=customer_memory,
        )

        response = self._generate_with_retry(client, prompt)

        text = getattr(response, "text", None)
        if not text or not text.strip():
            logger.warning("Gemini model returned empty or unavailable response.")
            return (
                "The advisor model returned an empty or unavailable response. "
                "No figures could be explained. Please verify property inputs and try again."
            )

        return text.strip()


def generate_llm_explanation(
    context_data: dict[str, Any],
    user_message: str,
    customer_memory: dict[str, Any] | None = None,
) -> str:
    """Compatibility function used by app.py."""
    advisor = GeminiAdvisor()
    return advisor.explain(
        computed_data=context_data,
        user_question=user_message,
        customer_memory=customer_memory,
    )

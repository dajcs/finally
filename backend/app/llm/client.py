"""LLM client using LiteLLM + OpenRouter with Cerebras inference."""

import json
import logging

from litellm import acompletion

from .prompts import SYSTEM_PROMPT, build_context_message
from .schemas import LLMResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


async def get_llm_response(messages: list[dict], context: dict) -> LLMResponse:
    """Call the LLM and return a structured LLMResponse.

    Args:
        messages: Conversation history (list of {role, content} dicts).
        context: Portfolio context dict with cash, positions, watchlist, total_value.

    Returns:
        Parsed LLMResponse with message, trades, and watchlist_changes.

    Raises:
        ValueError: If the LLM returns invalid/unparseable JSON.
    """
    context_text = build_context_message(context)

    full_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context_text},
        *messages,
    ]

    response = await acompletion(
        model=MODEL,
        messages=full_messages,
        response_format=LLMResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )

    raw = response.choices[0].message.content
    try:
        return LLMResponse.model_validate_json(raw)
    except Exception as e:
        logger.error("Failed to parse LLM response: %s | raw: %s", e, raw)
        raise ValueError(f"LLM returned invalid JSON: {e}") from e

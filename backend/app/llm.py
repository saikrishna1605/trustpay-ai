"""LLM client (Anthropic Messages API or any OpenAI-compatible chat API) returning parsed JSON.

`complete_json` returns None on network/parse failure. Callers keep their
deterministic rule results in that case and report the AI step as failed, so a
provider outage never silently turns into a "safe" verdict.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from .config import Settings

log = logging.getLogger("trustpay.llm")

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> Optional[dict[str, Any]]:
    match = _JSON_BLOCK.search(text or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


async def complete_json(settings: Settings, system: str, user: str, max_tokens: int = 1200) -> Optional[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_s) as client:
            if settings.llm_provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.llm_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.llm_model,
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                    },
                )
                resp.raise_for_status()
                text = "".join(b.get("text", "") for b in resp.json().get("content", []))
            else:
                resp = await client.post(
                    f"{settings.openai_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "max_tokens": max_tokens,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM call failed (%s); provider error details omitted to protect credentials", type(exc).__name__)
        return None
    parsed = extract_json(text)
    if parsed is None:
        log.warning("LLM returned non-JSON output")
    return parsed

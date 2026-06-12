import json
import os
import httpx
from app.config import settings

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _get_model() -> str:
    return settings.openrouter_model or "openai/gpt-4o-mini"


def _get_api_key() -> str:
    key = settings.openrouter_api_key
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    return key



async def chat(messages: list[dict], json_mode: bool = False) -> str:
    """Call OpenRouter chat completions. Returns the assistant text content."""
    payload: dict = {
        "model": _get_model(),
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://longchau-ai-triage.demo",
        "X-Title": "Long Chau AI Triage",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def chat_json(messages: list[dict]) -> dict:
    """Call OpenRouter and parse the response as JSON. Falls back to {} on parse error."""
    raw = await chat(messages, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON substring
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        return {}


def get_model_name() -> str:
    return _get_model()

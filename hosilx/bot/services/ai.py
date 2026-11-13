
"""Gemini AI adapteri. API kaliti va model faqat environment orqali olinadi."""
from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from ..config import Settings

log = logging.getLogger(__name__)


class AiError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind  # rate | timeout | network | provider | empty


class AiProvider(Protocol):
    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 800,
    ) -> str: ...


class GeminiProvider:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str):
        self._key = api_key
        self._model = model

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Anthropic formatidagi xabarlarni Gemini formatiga o'tkazadi."""
        contents = []

        for message in messages:
            role = message.get("role", "user")
            gemini_role = "model" if role in ("assistant", "model") else "user"
            raw_content = message.get("content", "")
            parts = []

            if isinstance(raw_content, str):
                if raw_content.strip():
                    parts.append({"text": raw_content})
            elif isinstance(raw_content, list):
                for item in raw_content:
                    if not isinstance(item, dict):
                        continue

                    if item.get("type") == "text":
                        value = item.get("text", "")
                        if value:
                            parts.append({"text": value})

                    elif item.get("type") == "image":
                        source = item.get("source", {})
                        if source.get("type") == "base64":
                            parts.append({
                                "inline_data": {
                                    "mime_type": source.get("media_type"),
                                    "data": source.get("data"),
                                }
                            })

            if parts:
                contents.append({
                    "role": gemini_role,
                    "parts": parts,
                })

        return contents

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 800,
    ) -> str:
        import aiohttp

        url = self.URL.format(model=self._model)

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._key,
        }

        payload = {
            "systemInstruction": {
                "parts": [{"text": system}]
            },
            "contents": self._convert_messages(messages),
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            },
        }

        try:
            timeout = aiohttp.ClientTimeout(total=45)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                ) as response:

                    if response.status == 429:
                        raise AiError("rate")

                    if response.status >= 400:
                        log.warning(
                            "Gemini API HTTP status: %s",
                            response.status,
                        )
                        raise AiError("provider")

                    data = await response.json()

        except asyncio.TimeoutError as exc:
            raise AiError("timeout") from exc

        except aiohttp.ClientError as exc:
            raise AiError("network") from exc

        candidates = data.get("candidates") or []

        if not candidates:
            raise AiError("empty")

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        result = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        if not result:
            raise AiError("empty")

        return result


def build_provider(s: Settings) -> AiProvider | None:
    """Gemini API sozlanmagan bo'lsa None qaytaradi."""
    if not s.gemini_api_key or not s.ai_model:
        return None

    return GeminiProvider(
        api_key=s.gemini_api_key,
        model=s.ai_model,
    )

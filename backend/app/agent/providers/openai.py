import os
import json
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, ValidationError
from backend.app.agent.base import BaseLLMProvider, LLMCompletionResponse, LLMMessage
from backend.app.config import get_settings
from backend.app.agent.providers.gemini import ProviderUnavailableError


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM Provider adapter."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMCompletionResponse:
        if not self.api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured in the environment.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if response.status_code != 200:
                raise ProviderUnavailableError(f"OpenAI API returned error {response.status_code}: {response.text}")
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return LLMCompletionResponse(content=content, provider="openai", model=self.model, raw_response=data)

    async def extract_structured_data(
        self,
        prompt: str,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        if not self.api_key:
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured in the environment.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        schema_json = json.dumps(schema.model_json_schema())
        system_msg = (
            f"You are a semantic extraction engine for IT support requests.\n"
            f"Extract parameters and output valid JSON matching this schema:\n"
            f"{schema_json}\n"
            f"Output pure JSON only."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if response.status_code != 200:
                raise ProviderUnavailableError(f"OpenAI API extraction failed: {response.text}")
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            try:
                return schema.model_validate_json(raw_text)
            except ValidationError as e:
                raise ProviderUnavailableError(f"Invalid structured schema returned by OpenAI: {e}")

import os
import json
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, ValidationError
from backend.app.agent.base import BaseLLMProvider, LLMCompletionResponse, LLMMessage
from backend.app.config import get_settings


class ProviderUnavailableError(Exception):
    """Raised when an external LLM provider cannot be reached or credentials are missing."""
    pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM Provider adapter."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = model

    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMCompletionResponse:
        if not self.api_key:
            raise ProviderUnavailableError("GEMINI_API_KEY is not configured in the environment.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        contents = [
            {"role": "user" if m.role in ["user", "system"] else "model", "parts": [{"text": m.content}]}
            for m in messages
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"contents": contents, "generationConfig": {"temperature": temperature}},
            )
            if response.status_code != 200:
                raise ProviderUnavailableError(f"Gemini API returned error {response.status_code}: {response.text}")

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ProviderUnavailableError("Gemini returned empty candidate list.")
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return LLMCompletionResponse(content=text, provider="gemini", model=self.model, raw_response=data)

    async def extract_structured_data(
        self,
        prompt: str,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        if not self.api_key:
            raise ProviderUnavailableError("GEMINI_API_KEY is not configured in the environment.")

        schema_json = json.dumps(schema.model_json_schema())
        system_instructions = (
            f"You are a semantic extraction engine for IT support requests.\n"
            f"Extract parameters from the following user request and output valid JSON matching this schema:\n"
            f"{schema_json}\n"
            f"Output JSON ONLY. Do not include markdown code blocks or additional text."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": f"{system_instructions}\n\nUser Request: {prompt}"}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise ProviderUnavailableError(f"Gemini API structured extraction failed: {response.text}")
            data = response.json()
            raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            try:
                return schema.model_validate_json(raw_text)
            except ValidationError as e:
                raise ProviderUnavailableError(f"Invalid structured schema returned by Gemini: {e}")

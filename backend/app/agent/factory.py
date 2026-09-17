from backend.app.config import get_settings
from backend.app.agent.base import BaseLLMProvider
from backend.app.agent.providers.mock import MockLLMProvider
from backend.app.agent.providers.gemini import GeminiProvider
from backend.app.agent.providers.openai import OpenAIProvider

settings = get_settings()


def get_llm_provider(provider_override: str | None = None) -> BaseLLMProvider:
    """
    Factory creating or returning the configured LLM provider.
    Supports 'mock', 'gemini', and 'openai'.
    """
    provider_name = (provider_override or settings.llm_provider).lower().strip()

    if provider_name == "gemini":
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.llm_model)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key)
    elif provider_name == "mock":
        return MockLLMProvider()
    else:
        # Default fallback to mock provider for safe offline development
        return MockLLMProvider()

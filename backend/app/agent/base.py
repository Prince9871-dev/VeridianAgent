from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str = Field(..., description="Role: system, user, assistant")
    content: str


class LLMCompletionResponse(BaseModel):
    content: str
    raw_response: Optional[Dict[str, Any]] = None
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None


class BaseLLMProvider(ABC):
    """
    Abstract LLM Provider interface.
    
    Guarantees loose coupling between the application and underlying model vendors
    (Google Gemini, OpenAI, Anthropic, or local/mock testing models).
    """

    @abstractmethod
    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMCompletionResponse:
        """Generate a natural language response."""
        pass

    @abstractmethod
    async def extract_structured_data(
        self,
        prompt: str,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """Extract structured entities or classifications adhering to a Pydantic schema."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider used for unit testing, offline development, and verification."""

    def __init__(self, default_response: str = "This is a mock LLM response for testing."):
        self.default_response = default_response

    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMCompletionResponse:
        return LLMCompletionResponse(
            content=self.default_response,
            provider="mock",
            model="mock-v1",
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        )

    async def extract_structured_data(
        self,
        prompt: str,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        # Returns a dummy instance of the requested schema
        return schema.model_construct()

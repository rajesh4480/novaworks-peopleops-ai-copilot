from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from collections.abc import AsyncIterator


class LLMSettings(BaseSettings):
    """
    Configuration for the LLM provider.
    """

    provider: str = Field(
        default="groq",
        validation_alias="LLM_PROVIDER",
    )

    groq_api_key: str | None = Field(
        default=None,
        validation_alias="GROQ_API_KEY",
    )

    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias="GROQ_MODEL",
    )

    openai_api_key: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )

    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias="OPENAI_MODEL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class LLMProvider(ABC):
    """
    Common interface for all LLM providers.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Generate a response from the LLM.
        """

        raise NotImplementedError
    @abstractmethod
    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """
        Stream response text chunks from the LLM.

        Each yielded string contains a partial piece of the response.
        """

        raise NotImplementedError


def get_llm_settings() -> LLMSettings:
    """
    Load LLM settings from environment variables.
    """

    return LLMSettings()


def get_llm_provider() -> LLMProvider:
    """
    Return the configured LLM provider.

    Supported:

        LLM_PROVIDER=groq
        LLM_PROVIDER=openai
    """

    settings = get_llm_settings()

    provider = settings.provider.lower().strip()

    if provider == "groq":

        from app.services.ai.providers.groq_provider import (
            GroqProvider,
        )

        return GroqProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

    if provider == "openai":

        from app.services.ai.providers.openai_provider import (
            OpenAIProvider,
        )

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    raise ValueError(
        f"Unsupported LLM provider: {settings.provider}"
    )
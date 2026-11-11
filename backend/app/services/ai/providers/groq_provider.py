from __future__ import annotations

from collections.abc import AsyncIterator

from groq import AsyncGroq

from app.services.ai.langsmith_tracing import record_token_usage
from app.services.ai.llm_provider import LLMProvider


class GroqProvider(LLMProvider):
    """Groq implementation of the common LLM provider interface."""

    def __init__(self, api_key: str | None, model: str):
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        self.client = AsyncGroq(api_key=api_key)
        self.model = model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using Groq and record token usage when available."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )

        try:
            record_token_usage(response.usage, model_name=self.model, provider="groq")
        except Exception:
            # Tracing must never break a successful model response.
            pass

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty response.")

        return content.strip()

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """Stream response text from Groq without changing stream request options."""
        stream_args = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "stream": True,
        }
        # Some OpenAI-compatible endpoints reject stream_options. Retry without
        # that optional field so token accounting cannot break chat streaming.
        try:
            stream = await self.client.chat.completions.create(
                **stream_args, stream_options={"include_usage": True}
            )
        except Exception:
            stream = await self.client.chat.completions.create(**stream_args)

        async for chunk in stream:
            # Streaming APIs report usage on the final chunk when requested.
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                try:
                    record_token_usage(usage, model_name=self.model, provider="groq")
                except Exception:
                    # Tracing must never break a successful streamed response.
                    pass

            if not chunk.choices:
                continue

            content = chunk.choices[0].delta.content
            if content:
                yield content

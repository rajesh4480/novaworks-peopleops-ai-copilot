from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from langsmith import traceable


def is_langsmith_enabled() -> bool:
    """Return True only when LangSmith tracing is explicitly enabled."""
    return (
        os.getenv("LANGSMITH_TRACING", "false").strip().lower()
        in {"true", "1", "yes"}
        and bool(os.getenv("LANGSMITH_API_KEY", "").strip())
    )


def normalize_token_usage(usage: Any) -> dict[str, int]:
    """Normalize OpenAI-compatible usage objects into LangSmith token fields.

    Providers may return dictionaries or SDK objects, and may use either
    OpenAI names (prompt_tokens/completion_tokens) or LangSmith names
    (input_tokens/output_tokens).
    """
    if usage is None:
        return {}

    def read_count(*names: str) -> int | None:
        for name in names:
            value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    input_tokens = read_count("input_tokens", "prompt_tokens")
    output_tokens = read_count("output_tokens", "completion_tokens")
    total_tokens = read_count("total_tokens")

    normalized: dict[str, int] = {}
    if input_tokens is not None:
        normalized["input_tokens"] = input_tokens
    if output_tokens is not None:
        normalized["output_tokens"] = output_tokens
    if total_tokens is not None:
        normalized["total_tokens"] = total_tokens
    elif input_tokens is not None and output_tokens is not None:
        normalized["total_tokens"] = input_tokens + output_tokens

    return normalized


def record_token_usage(
    usage: Any,
    model_name: str | None = None,
    provider: str | None = None,
) -> None:
    """Attach provider-reported token usage to the active LangSmith run.

    Updates both the required 'outputs' block for automatic cost-tracking,
    and fallback metadata fields for safety across different LangSmith SDK versions.
    """
    normalized = normalize_token_usage(usage)
    if not normalized or not is_langsmith_enabled():
        return

    try:
        from langsmith.run_helpers import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree is None:
            return

        # 1. Update outputs: LangSmith's Cost Estimator looks for usage_metadata here
        outputs = run_tree.outputs
        if outputs is None:
            outputs = {}
            run_tree.outputs = outputs
        outputs["usage_metadata"] = normalized

        # 2. Update metadata: Fallback for traditional table views & filters
        metadata = run_tree.metadata
        if metadata is None:
            metadata = {}
            run_tree.metadata = metadata
        
        metadata["usage_metadata"] = normalized
        metadata["token_usage"] = normalized
        
        if model_name:
            metadata["ls_model_name"] = model_name
            metadata["model_name"] = model_name
        if provider:
            metadata["ls_provider"] = provider
            metadata["provider"] = provider

        run_tree.patch()
    except Exception:
        # Observability is best-effort and must never break the model response.
        return


def _redact_policy_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Optional helper for deployments that choose to redact policy prompts."""
    return {
        "system_prompt": "[POLICY PROMPT REDACTED]",
        "user_prompt": "[USER QUESTION REDACTED]",
    }


def _redact_policy_output(output: Any) -> dict[str, str]:
    """Optional helper for deployments that choose to redact policy answers."""
    return {"output": "[POLICY ANSWER REDACTED]"}


@traceable(
    name="hr_policy_llm_generation",
    run_type="llm",
)
async def trace_policy_generation(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Generate a policy answer through the configured LLM provider.

    Captures usage attributes directly from the response if available,
    binding them securely to the current execution run tree.
    """
    from app.services.ai.llm_provider import get_llm_provider

    llm = get_llm_provider()

    # If your LLM provider returns a complex object containing token metadata,
    # capture it here and feed it directly into the run recorder.
    response = await llm.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    
    # Check if the response object contains metadata attributes (e.g., response.usage)
    if hasattr(response, "usage") and response.usage:
        record_token_usage(
            usage=response.usage,
            model_name=getattr(response, "model", None),
            provider=getattr(llm, "provider_name", None)
        )
    
    # Return string data gracefully to ensure full downstream structural safety
    return response if isinstance(response, str) else getattr(response, "text", str(response))


@traceable(
    name="hr_policy_llm_generation_stream",
    run_type="llm",
)
async def trace_policy_generation_stream(
    system_prompt: str,
    user_prompt: str,
) -> AsyncIterator[str]:
    """Stream a policy response through the configured LLM provider.

    Intercepts the async generator stream, checking for token usage structures
    emitted inside final stream chunks before completing execution.
    """
    from app.services.ai.llm_provider import get_llm_provider

    llm = get_llm_provider()

    async for chunk in llm.generate_stream(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    ):
        # Handle chunk formats that bundle token counts in the final block
        if hasattr(chunk, "usage") and chunk.usage:
            record_token_usage(
                usage=chunk.usage,
                model_name=getattr(chunk, "model", None),
                provider=getattr(llm, "provider_name", None)
            )
        elif isinstance(chunk, dict) and "usage" in chunk:
            record_token_usage(
                usage=chunk["usage"],
                model_name=chunk.get("model"),
                provider=getattr(llm, "provider_name", None)
            )
            
        # Yield the clean text segment back to the client application
        if isinstance(chunk, str):
            yield chunk
        elif hasattr(chunk, "text"):
            yield chunk.text
        elif isinstance(chunk, dict) and "text" in chunk:
            yield chunk["text"]

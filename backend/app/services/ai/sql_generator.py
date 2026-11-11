from __future__ import annotations

import re

from langsmith import traceable

from app.services.ai.llm_provider import get_llm_provider
from app.services.ai.sql_prompts import build_sql_generation_prompt


def clean_generated_sql(response: str) -> str:
    """
    Clean SQL returned by the LLM.

    The LLM is instructed not to use markdown fences,
    but we remove them defensively if they appear.
    """

    sql = response.strip()

    sql = re.sub(
        r"^```(?:sql)?\s*",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"\s*```$",
        "",
        sql,
    )

    return sql.strip()

@traceable(
    name="hr_sql_generation",
    run_type="llm",
    #process_inputs=lambda _inputs: {"input": "[REDACTED]"},
    #process_outputs=lambda _output: {"output": "[REDACTED]"},
    enabled=True,
)
async def generate_sql(
    schema_text: str,
    user_question: str,
) -> str:
    """
    Generate SQL for an HRMS question using the
    configured LLM provider.
    """

    system_prompt, user_prompt = build_sql_generation_prompt(
        schema_text=schema_text,
        user_question=user_question,
    )

    provider = get_llm_provider()

    response = await provider.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    sql = clean_generated_sql(response)

    if not sql:
        raise ValueError(
            "The LLM returned an empty SQL query."
        )

    return sql
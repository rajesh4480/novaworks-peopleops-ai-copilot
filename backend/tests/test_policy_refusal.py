import asyncio

from app.services.ai.policy_rag_service import answer_policy_question


async def main():
    question = (
        "What is the maximum amount of maternity leave available "
        "and how much salary is paid during maternity leave?"
    )

    result = await answer_policy_question(question)

    print()
    print("=" * 70)
    print("POLICY RAG REFUSAL TEST")
    print("=" * 70)
    print(result.answer)

    print()
    print("=" * 70)
    print("SOURCES")
    print("=" * 70)

    for source in result.sources:
        print(source)


if __name__ == "__main__":
    asyncio.run(main())
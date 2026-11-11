import asyncio

from app.services.ai.policy_rag_service import answer_policy_question


async def main():
    question = "What is the company's policy for quantum physics research?"

    result = await answer_policy_question(question)

    print()
    print("=" * 70)
    print("POLICY RAG UNRELATED QUERY TEST")
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
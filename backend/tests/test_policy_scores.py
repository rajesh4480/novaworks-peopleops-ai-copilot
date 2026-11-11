from app.services.ai.policy_retriever import retrieve_policy_chunks


queries = [
    "How many days of casual, sick, and earned leave are available?",
    "What is the work from home approval policy?",
    "What is the company's policy for quantum physics research?",
]


for query in queries:
    print()
    print("=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    results = retrieve_policy_chunks(query, top_k=5)

    for index, result in enumerate(results, start=1):
        document = result.document

        print()
        print(f"Result {index}")
        print(f"Score: {result.score:.6f}")
        print(f"Title: {document.metadata.get('title')}")
        print(f"Source: {document.metadata.get('source_file')}")
        print(f"Content: {document.page_content[:200]}")
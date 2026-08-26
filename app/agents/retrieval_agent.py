from app.rag import search_knowledge


def retrieve_knowledge(question: str):

    results = search_knowledge(
        question,
        top_k=1
    )

    return results
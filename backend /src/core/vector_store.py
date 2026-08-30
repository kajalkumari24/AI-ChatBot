from langchain_chroma import Chroma
from src.config import settings
from src.core.embeddings import embedding_model

_vector_store = None

# Chroma's default distance is cosine distance: 0 = identical, 2 = opposite.
# Anything below this threshold is considered "actually relevant".
RELEVANCE_THRESHOLD = 0.8


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    _vector_store = Chroma(
        collection_name="chatbot-documents",
        embedding_function=embedding_model,
        persist_directory=settings.CHROMA_DB_DIR,
    )
    return _vector_store


def add_document(doc_id: str, text: str, metadata: dict | None = None):
    store = get_vector_store()
    store.add_texts(texts=[text], metadatas=[metadata or {}], ids=[doc_id])


def search(query: str, top_k: int = 3) -> list[str]:
    """
    Only returns chunks that are actually relevant to the query, so
    unrelated document content doesn't leak into unrelated questions
    (e.g. an image-conversion request pulling in an unrelated text chunk).
    """
    store = get_vector_store()
    if store._collection.count() == 0:
        return []

    results_with_scores = store.similarity_search_with_score(query, k=top_k)
    return [
        doc.page_content
        for doc, score in results_with_scores
        if score <= RELEVANCE_THRESHOLD
    ]


if __name__ == "__main__":
    print("Testing ChromaDB connection...")
    print("Using CHROMA_DB_DIR:", settings.CHROMA_DB_DIR)
    store = get_vector_store()
    count = store._collection.count()
    print("Collection ready. Current document count:", count)
    print("vector_store.py OK")

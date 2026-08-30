from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings

_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


class FastEmbedEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in _model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(_model.embed([text]))[0].tolist()


embedding_model = FastEmbedEmbeddings()


def embed_text(text: str) -> list[float]:
    return embedding_model.embed_query(text)


if __name__ == "__main__":
    print("Testing embeddings...")
    vec = embed_text("hello world")
    print("Embedding length:", len(vec))
    print("First 5 values:", vec[:5])
    print("embeddings.py OK")

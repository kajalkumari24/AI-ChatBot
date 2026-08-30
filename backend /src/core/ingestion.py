from pathlib import Path
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.vector_store import get_vector_store

RAW_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw_documents"


def load_and_split_documents():
    """Loads documents from raw_documents folder and splits into chunks."""
    if not RAW_DOCS_DIR.exists():
        RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    pdf_loader = PyPDFDirectoryLoader(str(RAW_DOCS_DIR))
    txt_loader = DirectoryLoader(str(RAW_DOCS_DIR), glob="**/*.txt", loader_cls=TextLoader)

    documents = []
    documents.extend(pdf_loader.load())
    documents.extend(txt_loader.load())

    if not documents:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunks = text_splitter.split_documents(documents)
    return chunks


def ingest_documents_to_db():
    """Processes documents and stores them in ChromaDB."""
    chunks = load_and_split_documents()
    if not chunks:
        return {"status": "No documents found to ingest", "documents_processed": 0, "chunks_created": 0}

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    return {
        "status": "Success",
        "documents_processed": len(set(doc.metadata.get("source") for doc in chunks)),
        "chunks_created": len(chunks)
    }


if __name__ == "__main__":
    result = ingest_documents_to_db()
    print("Ingestion Result:", result)

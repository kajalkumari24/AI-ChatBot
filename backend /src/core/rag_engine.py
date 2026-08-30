from typing import Optional
from PIL import Image
from src.core.vector_store import search
from src.core.llm import get_llm_response
from src.services import memory


def build_context_block(chunks: list[str]) -> str:
    if not chunks:
        return ""
    joined = "\n---\n".join(chunks)
    return (
        f"Retrieved Document Context:\n{joined}\n\n"
        "Instruction: Use the context above only if it is actually relevant "
        "to the question below. Otherwise, ignore it and answer normally.\n\n"
    )


def ask(
    session_id: str,
    user_message: str,
    image: Optional[Image.Image] = None,
    top_k: int = 3,
) -> str:
    if image is not None:
        context_block = ""
    else:
        chunks = search(user_message, top_k=top_k)
        context_block = build_context_block(chunks)

    history = memory.get_history(session_id) or []
    prompt = f"{context_block}User Question: {user_message}" if context_block else user_message

    reply = get_llm_response(prompt, history=history, image=image)

    stored_user_msg = f"[Image Uploaded] {user_message}" if image else user_message
    memory.append_message(session_id, "user", stored_user_msg)
    memory.append_message(session_id, "assistant", reply)

    return reply


if __name__ == "__main__":
    print("Testing full RAG engine...")
    reply = ask("rag-engine-test", "hello")
    print("Reply:", reply)
    print("rag_engine.py OK")

from typing import Optional
from PIL import Image

from src.core.vector_store import search
from src.core.llm import get_llm_response
from src.services import memory



def build_context_block(
    chunks: list[str]
) -> str:

    if not chunks:
        return ""

    joined = "\n---\n".join(chunks)

    return (
        f"Retrieved Document Context:\n"
        f"{joined}\n\n"
        "Instruction: Use the context above if relevant. "
        "Otherwise, answer normally.\n\n"
    )



def ask(
    session_id: str,
    user_message: str,
    image: Optional[Image.Image] = None,
    top_k: int = 3
) -> str:

    try:

        
        chunks = search(
            user_message,
            top_k=top_k
        )


        
        context_block = build_context_block(
            chunks
        )


        
        history = memory.get_history(
            session_id
        ) or []

        if context_block:

            prompt = (
                f"{context_block}"
                f"User Question: {user_message}"
            )

        else:

            prompt = user_message


    
        reply = get_llm_response(
            prompt,
            history=history,
            image=image
        )


       
        if image:

            stored_user_msg = (
                f"[Image Uploaded] {user_message}"
            )

        else:

            stored_user_msg = user_message


        memory.append_message(
            session_id,
            "user",
            stored_user_msg
        )


        memory.append_message(
            session_id,
            "assistant",
            reply
        )


        return reply


  
    except Exception as e:

        error_msg = str(e)

        if "NOT_FOUND" in error_msg:

            return (
                "⚠️ **Configuration Error:** "
                "The specified Gemini model was not found. "
                "Please check `LLM_MODEL` in your `.env` file."
            )


       
        elif (
            "RESOURCE_EXHAUSTED" in error_msg
            or "429" in error_msg
        ):

            return (
                "⚠️ **Rate Limit Exceeded:** "
                "Free tier quota reached. "
                "Please wait and try again."
            )

        else:

            return (
                f"⚠️ **Error:** {error_msg}"
            )
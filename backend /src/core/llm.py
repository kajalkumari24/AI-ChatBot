import re
import base64
import io
from typing import Optional
from PIL import Image

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config import settings
from src.core.prompts import SYSTEM_PROMPT

llm = ChatGroq(
    groq_api_key=settings.GROQ_API_KEY,
    model=settings.LLM_MODEL,
    temperature=0.3
)

vision_llm = ChatGroq(
    groq_api_key=settings.GROQ_API_KEY,
    model=settings.VISION_MODEL,
    temperature=0.3
)


def _extract_text(content) -> str:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        text = "".join(parts)
    else:
        text = str(content)

    # Strip internal reasoning traces some models include (e.g. <think>...</think>)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


def _image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image_format = image.format if image.format else "PNG"
    image.save(buffer, format=image_format)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime_type = f"image/{image_format.lower()}"
    return f"data:{mime_type};base64,{encoded}"


def get_llm_response(
    user_message: str,
    history: list[dict] | None = None,
    image: Optional[Image.Image] = None
) -> str:
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if history:
        for h in history[-6:]:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                messages.append(AIMessage(content=h["content"]))

    if image:
        image_data_uri = _image_to_base64(image)
        content_blocks = [
            {"type": "text", "text": user_message},
            {"type": "image_url", "image_url": {"url": image_data_uri}}
        ]
        messages.append(HumanMessage(content=content_blocks))
    else:
        messages.append(HumanMessage(content=user_message))

    active_llm = vision_llm if image else llm
    response = active_llm.invoke(messages)
    return _extract_text(response.content)


if __name__ == "__main__":
    print("Testing LLM connection...")
    reply = get_llm_response("Say hello, connection works and nothing else.")
    print("LLM reply:", reply)
    print("llm.py OK")
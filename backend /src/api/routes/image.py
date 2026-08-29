import os
import base64
import logging

from fastapi import APIRouter, Form, HTTPException
from google import genai
from google.genai import types

from src.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy-initialized client so a missing key doesn't crash the app on startup
_gemini_client = None


def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail=(
                    "GEMINI_API_KEY is missing. Set it in your .env file to "
                    "enable image generation."
                ),
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def generate_gemini_image(prompt: str) -> str:
    """Generate image via Gemini Imagen 3 and return Base64 string."""
    client = get_gemini_client()
    result = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="1:1",
        ),
    )

    if not result.generated_images:
        raise HTTPException(status_code=502, detail="Gemini returned no image data.")

    image_bytes = result.generated_images[0].image.image_bytes
    return base64.b64encode(image_bytes).decode("utf-8")


@router.post("/image")
async def generate_image(prompt: str = Form(...)):
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        image_base64 = generate_gemini_image(prompt)
        return {"image_url": f"data:image/jpeg;base64,{image_base64}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Gemini image generation failed")
        raise HTTPException(status_code=502, detail=f"Image generation failed: {str(e)}")
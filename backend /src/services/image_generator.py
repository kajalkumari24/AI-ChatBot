import os
import requests


def generate_image(prompt: str):

    api_key = os.getenv("IMAGE_API_KEY")

    if not api_key:

        return {
            "success": False,
            "message": "Image generation is not configured."
        }

    try:

        response = requests.post(
            os.getenv(
                "IMAGE_API_URL",
                "https://api.openai.com/v1/images/generations"
            ),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": prompt,
                "size": "1024x1024"
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        image_url = (
            data["data"][0].get("url")
        )

        return {
            "success": True,
            "url": image_url
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }
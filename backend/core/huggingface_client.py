from __future__ import annotations

import io

import httpx
from PIL import Image, ImageDraw

from core.config import settings


class HuggingFaceClient:
    def __init__(self) -> None:
        self._timeout = settings.request_timeout_seconds
        self._base_url = "https://api-inference.huggingface.co/models"

    @property
    def is_configured(self) -> bool:
        return bool(settings.huggingface_api_key.strip())

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.huggingface_api_key}",
            "Content-Type": "application/json",
        }

    async def generate_text(self, prompt: str, *, max_new_tokens: int = 180) -> str:
        if not self.is_configured:
            return self._offline_text_fallback(prompt)

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "return_full_text": False,
                "temperature": 0.7,
            },
        }
        url = f"{self._base_url}/{settings.text_model_id}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list) and data and "generated_text" in data[0]:
            return str(data[0]["generated_text"]).strip()
        if isinstance(data, dict) and "generated_text" in data:
            return str(data["generated_text"]).strip()

        return self._offline_text_fallback(prompt)

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int,
        height: int,
    ) -> bytes:
        if not self.is_configured:
            return self._offline_image_fallback(prompt, width, height)

        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
            },
        }
        url = f"{self._base_url}/{settings.image_model_id}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            if response.headers.get("content-type", "").startswith("application/json"):
                raise RuntimeError(f"Image API returned JSON error: {response.text}")
            return response.content

    @staticmethod
    def _offline_text_fallback(prompt: str) -> str:
        return (
            "High-quality social media marketing visual, ultra-detailed, "
            "professional lighting, brand-focused composition. Product idea: "
            f"{prompt.strip()}"
        )

    @staticmethod
    def _offline_image_fallback(prompt: str, width: int, height: int) -> bytes:
        image = Image.new("RGB", (width, height), color=(243, 242, 236))
        draw = ImageDraw.Draw(image)
        draw.rectangle((25, 25, width - 25, height - 25), outline=(40, 40, 40), width=4)
        text = "OFFLINE PREVIEW\n" + prompt[:100]
        draw.multiline_text((40, 40), text, fill=(20, 20, 20), spacing=6)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()


hf_client = HuggingFaceClient()

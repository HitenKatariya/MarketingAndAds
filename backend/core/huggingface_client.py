from __future__ import annotations

import asyncio
import io
from typing import Any

import httpx
from loguru import logger
from PIL import Image, ImageDraw, ImageOps

from core.config import settings


class HuggingFaceClient:
    def __init__(self) -> None:
        self._timeout = settings.request_timeout_seconds
        self._base_url = settings.hf_inference_base_url.rstrip("/")
        self.last_text_model_used: str | None = None
        self.last_image_model_used: str | None = None
        self.last_image_source: str = "unknown"
        self.last_issue: str = ""

        logger.info("HF client initialized with base_url={base_url}", base_url=self._base_url)

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
            self.last_text_model_used = "offline-fallback"
            self.last_issue = "HF token not configured"
            logger.warning("HF text generation skipped: token not configured. Using fallback text.")
            return self._offline_text_fallback(prompt)

        self.last_text_model_used = settings.text_model_id
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "return_full_text": False,
                "temperature": 0.7,
            },
        }
        url = f"{self._base_url}/{settings.text_model_id}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for attempt in range(1, 4):
                    logger.info(
                        "HF text attempt {attempt}/3 endpoint={endpoint} model={model}",
                        attempt=attempt,
                        endpoint=self._base_url,
                        model=settings.text_model_id,
                    )
                    response = await client.post(url, headers=self._headers(), json=payload)
                    if response.status_code == 503:
                        wait_seconds = self._get_estimated_wait_seconds(response)
                        self.last_issue = (
                            f"Text model loading: {settings.text_model_id}; waiting {wait_seconds}s"
                        )
                        logger.warning(self.last_issue)
                        await asyncio.sleep(wait_seconds)
                        continue
                    response.raise_for_status()
                    data = response.json()

                    if isinstance(data, dict) and data.get("error"):
                        # Some models return a JSON object with estimated loading time.
                        wait_seconds = self._get_estimated_wait_seconds(response)
                        self.last_issue = (
                            f"Text model error on {settings.text_model_id}: {data.get('error')}"
                        )
                        logger.warning(self.last_issue)
                        await asyncio.sleep(wait_seconds)
                        continue
                    break
                else:
                    self.last_text_model_used = "offline-fallback"
                    self.last_issue = (
                        f"Text model unavailable after retries: {settings.text_model_id}"
                    )
                    logger.error(self.last_issue)
                    return self._offline_text_fallback(prompt)
        except httpx.HTTPError as exc:
            self.last_text_model_used = "offline-fallback"
            self.last_issue = f"Text HTTP error for {settings.text_model_id}: {exc}"
            logger.error(self.last_issue)
            return self._offline_text_fallback(prompt)

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
            self.last_image_model_used = "offline-fallback"
            self.last_image_source = "offline"
            self.last_issue = "HF token not configured"
            logger.warning("HF image generation skipped: token not configured. Using fallback image.")
            return self._offline_image_fallback(prompt, width, height)

        # Try configured model first, then known alternatives.
        model_candidates = [
            settings.image_model_id,
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/stable-diffusion-2-1",
        ]
        model_candidates = list(dict.fromkeys(model_candidates))

        for model_id in model_candidates:
            logger.info("HF image generation trying model={model}", model=model_id)
            image = await self._generate_image_from_model(
                model_id=model_id,
                prompt=prompt,
                width=width,
                height=height,
            )
            if image is not None:
                self.last_image_model_used = model_id
                self.last_image_source = "online"
                self.last_issue = ""
                logger.info("HF image success with model={model}", model=model_id)
                return image

        self.last_image_model_used = "offline-fallback"
        self.last_image_source = "offline"
        if not self.last_issue:
            self.last_issue = "All configured image models failed"
        logger.error("HF image generation failed for all models. Using fallback image.")
        return self._offline_image_fallback(prompt, width, height)

    async def _generate_image_from_model(
        self,
        *,
        model_id: str,
        prompt: str,
        width: int,
        height: int,
    ) -> bytes | None:
        payload = {
            "inputs": prompt,
        }
        url = f"{self._base_url}/{model_id}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for attempt in range(1, 4):
                    logger.info(
                        "HF image attempt {attempt}/3 endpoint={endpoint} model={model}",
                        attempt=attempt,
                        endpoint=self._base_url,
                        model=model_id,
                    )
                    response = await client.post(url, headers=self._headers(), json=payload)

                    if response.status_code == 503:
                        wait_seconds = self._get_estimated_wait_seconds(response)
                        self.last_issue = f"Image model loading: {model_id}; waiting {wait_seconds}s"
                        logger.warning(self.last_issue)
                        await asyncio.sleep(wait_seconds)
                        continue

                    if response.headers.get("content-type", "").startswith("application/json"):
                        # Often contains loading/availability errors.
                        try:
                            error_data = response.json()
                        except Exception:
                            error_data = {}
                        self.last_issue = f"Image JSON error from {model_id}: {error_data}"
                        logger.warning(self.last_issue)
                        wait_seconds = self._get_estimated_wait_seconds(response)
                        if wait_seconds > 0:
                            await asyncio.sleep(wait_seconds)
                            continue
                        return None

                    response.raise_for_status()
                    return self._resize_image_bytes(response.content, width, height)
        except httpx.HTTPError as exc:
            self.last_issue = f"Image HTTP error for {model_id}: {exc}"
            logger.warning(self.last_issue)
            return None

        return None

    @staticmethod
    def _resize_image_bytes(image_bytes: bytes, width: int, height: int) -> bytes:
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb = image.convert("RGB")
            fitted = ImageOps.fit(rgb, (width, height), method=Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            fitted.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer.read()

    @staticmethod
    def _get_estimated_wait_seconds(response: httpx.Response) -> int:
        try:
            data: Any = response.json()
        except Exception:
            return 0

        if isinstance(data, dict):
            estimated = data.get("estimated_time")
            if isinstance(estimated, (int, float)):
                return max(1, min(int(estimated), 25))
        return 0

    def diagnostics(self) -> dict[str, str]:
        return {
            "inference_base_url": self._base_url,
            "text_model_configured": settings.text_model_id,
            "image_model_configured": settings.image_model_id,
            "last_text_model_used": self.last_text_model_used or "unknown",
            "last_image_model_used": self.last_image_model_used or "unknown",
            "last_image_source": self.last_image_source,
            "last_issue": self.last_issue or "none",
        }

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

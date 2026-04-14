from __future__ import annotations

import asyncio
import io
from typing import Any

from loguru import logger
from PIL import Image, ImageDraw, ImageOps
from transformers import T5Tokenizer, T5ForConditionalGeneration

from core.config import settings, get_hf_api_key
from huggingface_hub import InferenceClient


class HuggingFaceClient:
    MAX_WAIT_SECONDS = 300
    TEXT_MODEL_NAME = "google/flan-t5-base"
    IMAGE_MODEL_NAME = "stabilityai/stable-diffusion-xl-base-1.0"

    def __init__(self) -> None:
        self.tokenizer = None
        self.text_model = None
        self.last_text_model_used: str | None = None
        self.last_image_model_used: str | None = None
        self.last_image_source: str = "unknown"
        self.last_issue: str = ""
        self._init_text_model()
        logger.info("HF client initialized")

    def _init_text_model(self):
        try:
            logger.info("Loading T5 model locally...")
            self.tokenizer = T5Tokenizer.from_pretrained(self.TEXT_MODEL_NAME)
            self.text_model = T5ForConditionalGeneration.from_pretrained(self.TEXT_MODEL_NAME)
            logger.info("T5 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load T5 model: {e}")
            self.last_issue = f"Model load error: {e}"

    @property
    def is_configured(self) -> bool:
        return bool(get_hf_api_key())

    async def generate_text(self, prompt: str, model_id: str, *, max_new_tokens: int = 180) -> str:
        if not self.is_configured:
            self.last_issue = "HF token not configured"
            logger.warning("HF text: using offline fallback")
            return self._offline_text_fallback(prompt)

        if self.text_model is None or self.tokenizer is None:
            self.last_issue = "Text model not loaded"
            logger.warning("Text model not loaded, using offline fallback")
            return self._offline_text_fallback(prompt)

        self.last_text_model_used = model_id

        try:
            logger.info("Generating text with T5 locally...")

            loop = asyncio.get_event_loop()
            inputs = await loop.run_in_executor(
                None,
                lambda: self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            )

            outputs = await loop.run_in_executor(
                None,
                lambda: self.text_model.generate(
                    inputs.input_ids,
                    max_new_tokens=max_new_tokens,
                    num_beams=4,
                    do_sample=True,
                    temperature=0.7,
                )
            )

            result = await loop.run_in_executor(
                None,
                lambda: self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            )

            logger.info(f"Text generation success")
            return result

        except Exception as e:
            self.last_issue = f"Text generation error: {e}"
            logger.error(self.last_issue)
            return self._offline_text_fallback(prompt)

    async def generate_image(self, prompt: str, model_id: str, *, width: int, height: int) -> bytes:
        if not self.is_configured:
            self.last_image_model_used = "offline-fallback"
            self.last_image_source = "offline"
            self.last_issue = "HF token not configured"
            logger.warning("HF image: using offline fallback")
            return self._offline_image_fallback(prompt, width, height)

        api_key = get_hf_api_key()
        self.last_image_model_used = model_id

        try:
            logger.info("Generating image with nscale provider...")

            client = InferenceClient(
                provider="nscale",
                api_key=api_key,
            )

            image = client.text_to_image(
                prompt=prompt,
                model=self.IMAGE_MODEL_NAME,
                width=width,
                height=height,
            )

            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()

            self.last_image_source = "online"
            logger.info(f"Image generation success: {len(image_bytes)} bytes")
            return image_bytes

        except Exception as e:
            self.last_image_source = "error"
            self.last_issue = f"Image generation error: {e}"
            logger.error(self.last_issue)
            return self._offline_image_fallback(prompt, width, height)

    def diagnostics(self) -> dict[str, str]:
        return {
            "text_model": self.TEXT_MODEL_NAME,
            "image_model": self.IMAGE_MODEL_NAME,
            "text_model_loaded": "yes" if self.text_model is not None else "no",
            "last_text_model_used": self.last_text_model_used or "unknown",
            "last_image_model_used": self.last_image_model_used or "unknown",
            "last_image_source": self.last_image_source,
            "last_issue": self.last_issue or "none",
            "is_configured": "yes" if self.is_configured else "no",
        }

    @staticmethod
    def _offline_text_fallback(prompt: str) -> str:
        return (
            "High-quality social media marketing visual, ultra-detailed, "
            "professional lighting, brand-focused composition. Product: "
            f"{prompt.strip()}"
        )

    @staticmethod
    def _offline_image_fallback(prompt: str, width: int, height: int) -> bytes:
        image = Image.new("RGB", (width, height), color=(243, 242, 236))
        draw = ImageDraw.Draw(image)
        draw.rectangle((25, 25, width - 25, height - 25), outline=(40, 40, 40), width=4)
        text = "OFFLINE PREVIEW\n" + prompt[:80]
        draw.multiline_text((40, 40), text, fill=(20, 20, 20), spacing=6)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()


hf_client = HuggingFaceClient()

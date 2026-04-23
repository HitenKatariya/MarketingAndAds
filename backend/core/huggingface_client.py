from __future__ import annotations

import asyncio
import base64
import contextvars
import io
import re
from typing import Any

import httpx
from loguru import logger
from PIL import Image, ImageDraw, ImageOps
try:
    from transformers import T5Tokenizer, T5ForConditionalGeneration
except Exception:  # Optional in lightweight/runtime builds
    T5Tokenizer = None  # type: ignore[assignment]
    T5ForConditionalGeneration = None  # type: ignore[assignment]

from core.config import settings, get_hf_api_key, get_together_api_key
from huggingface_hub import InferenceClient


class HuggingFaceClient:
    MAX_WAIT_SECONDS = 300
    TEXT_MODEL_NAME = "google/flan-t5-base"
    IMAGE_MODEL_NAME = "stabilityai/stable-diffusion-xl-base-1.0"

    def __init__(self) -> None:
        self.tokenizer = None
        self.text_model = None
        self.local_image_pipe = None
        self._request_hf_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            "request_hf_token",
            default=None,
        )
        self._request_image_mode: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            "request_image_mode",
            default=None,
        )
        self.last_text_model_used: str | None = None
        self.last_image_model_used: str | None = None
        self.last_image_source: str = "unknown"
        self.last_issue: str = ""
        logger.info("HF client initialized")

    def _init_text_model(self) -> None:
        if T5Tokenizer is None or T5ForConditionalGeneration is None:
            self.last_issue = "transformers not installed in this environment"
            logger.warning("Skipping local text model init: transformers is not installed")
            self.tokenizer = None
            self.text_model = None
            return

        try:
            logger.info("Loading T5 model locally...")
            self.tokenizer = T5Tokenizer.from_pretrained(self.TEXT_MODEL_NAME)
            self.text_model = T5ForConditionalGeneration.from_pretrained(self.TEXT_MODEL_NAME)
            logger.info("T5 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load T5 model: {e}")
            self.last_issue = f"Model load error: {e}"
            self.tokenizer = None
            self.text_model = None

    def ensure_text_model_loaded(self, *, fail_fast: bool = False) -> None:
        if self.text_model is not None and self.tokenizer is not None:
            return

        self._init_text_model()

        if self.text_model is None or self.tokenizer is None:
            error_msg = (
                "Text model failed to load during startup. "
                f"Reason: {self.last_issue or 'unknown error'}"
            )
            if fail_fast:
                raise RuntimeError(error_msg)
            logger.warning(error_msg)

    @property
    def is_configured(self) -> bool:
        return bool(self._effective_hf_key() or self._effective_together_key())

    def push_request_overrides(self, hf_token: str | None = None, image_mode: str | None = None) -> tuple[Any, Any]:
        token_reset = self._request_hf_token.set(hf_token.strip() if hf_token else None)
        mode = image_mode.strip().lower() if image_mode else None
        mode_reset = self._request_image_mode.set(mode if mode in {"online", "local"} else None)
        return token_reset, mode_reset

    def pop_request_overrides(self, reset_tokens: tuple[Any, Any]) -> None:
        token_reset, mode_reset = reset_tokens
        self._request_hf_token.reset(token_reset)
        self._request_image_mode.reset(mode_reset)

    def _effective_hf_key(self) -> str:
        request_token = self._request_hf_token.get()
        if request_token:
            return request_token
        return get_hf_api_key()

    @staticmethod
    def _effective_together_key() -> str:
        return get_together_api_key()

    async def generate_text(self, prompt: str, model_id: str, *, max_new_tokens: int = 180) -> str:
        self.last_text_model_used = model_id

        hf_key = self._effective_hf_key()
        if hf_key:
            try:
                logger.info(f"Generating text online with HF model: {model_id}")
                result = await self._generate_text_online(prompt, model_id, max_new_tokens=max_new_tokens)
                if result:
                    logger.info("HF online text generation success")
                    return result
            except Exception as e:
                self.last_issue = f"HF online text generation error: {e}"
                logger.error(self.last_issue)

        together_key = self._effective_together_key()
        if together_key:
            try:
                logger.info("Generating text online with Together API")
                result = await self._generate_text_together(prompt, max_new_tokens=max_new_tokens)
                if result:
                    self.last_text_model_used = settings.together_text_model_id
                    logger.info("Together text generation success")
                    return result
            except Exception as e:
                self.last_issue = f"Together text generation error: {e}"
                logger.error(self.last_issue)

        if not self.is_configured:
            self.last_issue = "No online text provider token configured"
            logger.warning("No HF/Together text token configured, using offline fallback")
            return self._offline_text_fallback(prompt)

        if self.text_model is None or self.tokenizer is None:
            self.last_issue = "Text model not loaded"
            logger.warning("Text model not loaded, using offline fallback")
            return self._offline_text_fallback(prompt)

        try:
            logger.info("Generating text with local T5 fallback...")

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
        if self._request_image_mode.get() == "local":
            logger.info("Image mode forced to local CPU by request header")
            try:
                image_bytes = await self._generate_image_local_cpu(prompt, width=width, height=height)
                self.last_image_model_used = "local-cpu-sd15"
                self.last_image_source = "local-cpu"
                return image_bytes
            except Exception as local_error:
                self.last_image_model_used = "offline-fallback"
                self.last_image_source = "offline"
                self.last_issue = f"Forced local mode failed: {local_error}"
                logger.error(self.last_issue)
                return self._offline_image_fallback(prompt, width, height)

        if not self.is_configured:
            self.last_issue = "No HF/Together token configured - using local CPU fallback"
            logger.warning("No image API token configured, trying local CPU image generation")
            try:
                image_bytes = await self._generate_image_local_cpu(prompt, width=width, height=height)
                self.last_image_model_used = "local-cpu-sd15"
                self.last_image_source = "local-cpu"
                return image_bytes
            except Exception as local_error:
                self.last_image_model_used = "offline-fallback"
                self.last_image_source = "offline"
                self.last_issue = f"Local CPU fallback failed: {local_error}"
                logger.error(self.last_issue)
                return self._offline_image_fallback(prompt, width, height)

        api_key = self._effective_hf_key()
        self.last_image_model_used = model_id

        if api_key:
            try:
                logger.info("Generating image with HF nscale provider...")

                client = InferenceClient(
                    provider="nscale",
                    api_key=api_key,
                )

                try:
                    image = client.text_to_image(
                        prompt=prompt,
                        model=model_id,
                        width=width,
                        height=height,
                        guidance_scale=9.0,
                        num_inference_steps=55,
                    )
                except TypeError:
                    image = client.text_to_image(
                        prompt=prompt,
                        model=model_id,
                        width=width,
                        height=height,
                    )

                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()

                self.last_image_source = "online"
                logger.info(f"HF image generation success: {len(image_bytes)} bytes")
                return image_bytes
            except Exception as e:
                self.last_image_source = "error"
                self.last_issue = f"HF image generation error: {e}"
                logger.error(self.last_issue)
                error_text = str(e)
                if "402" in error_text and "Payment Required" in error_text:
                    logger.warning("HF provider billing rejected request, trying Together/local fallback")

        together_key = self._effective_together_key()
        if together_key:
            try:
                logger.info("Generating image with Together API...")
                image_bytes = await self._generate_image_together(prompt, width=width, height=height)
                self.last_image_model_used = settings.together_image_model_id
                self.last_image_source = "online-together"
                logger.info(f"Together image generation success: {len(image_bytes)} bytes")
                return image_bytes
            except Exception as e:
                self.last_issue = f"Together image generation error: {e}"
                logger.error(self.last_issue)

        try:
            image_bytes = await self._generate_image_local_cpu(prompt, width=width, height=height)
            self.last_image_model_used = "local-cpu-sd15"
            self.last_image_source = "local-cpu"
            self.last_issue = "Online providers unavailable - local CPU fallback used"
            return image_bytes
        except Exception as local_error:
            raise RuntimeError(
                "All image providers failed and local CPU fallback also failed. "
                f"Fallback error: {local_error}"
            ) from local_error

    async def _generate_text_online(self, prompt: str, model_id: str, *, max_new_tokens: int) -> str:
        api_key = self._effective_hf_key()
        loop = asyncio.get_event_loop()

        def _call() -> str:
            client = InferenceClient(api_key=api_key)
            output = client.text_generation(
                model=model_id,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                do_sample=True,
                return_full_text=False,
            )
            if isinstance(output, str):
                return output.strip()
            text = str(output).strip()
            text = re.sub(r"\s+", " ", text)
            return text

        return await loop.run_in_executor(None, _call)

    async def _generate_text_together(self, prompt: str, *, max_new_tokens: int) -> str:
        api_key = self._effective_together_key()
        if not api_key:
            return ""

        url = "https://api.together.xyz/v1/chat/completions"
        payload = {
            "model": settings.together_text_model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.7,
            "max_tokens": max_new_tokens,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        timeout = max(120, settings.request_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        return re.sub(r"\s+", " ", str(content)).strip()

    async def _generate_image_together(self, prompt: str, *, width: int, height: int) -> bytes:
        api_key = self._effective_together_key()
        if not api_key:
            raise RuntimeError("Together API key missing")

        url = "https://api.together.xyz/v1/images/generations"
        payload = {
            "model": settings.together_image_model_id,
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": 28,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        timeout = max(180, settings.request_timeout_seconds * 2)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        image_data = (data.get("data") or [{}])[0]
        b64 = image_data.get("b64_json")
        if b64:
            return base64.b64decode(b64)

        image_url = image_data.get("url")
        if image_url:
            async with httpx.AsyncClient(timeout=timeout) as client:
                image_resp = await client.get(image_url)
                image_resp.raise_for_status()
                return image_resp.content

        raise RuntimeError("Together returned no image payload")

    async def _generate_image_local_cpu(self, prompt: str, *, width: int, height: int) -> bytes:
        loop = asyncio.get_event_loop()

        def _run_local() -> bytes:
            try:
                from diffusers import StableDiffusionPipeline
            except Exception as exc:
                raise RuntimeError("Local CPU mode requires the 'diffusers' package") from exc

            if self.local_image_pipe is None:
                logger.info("Loading local CPU image pipeline (stable-diffusion-v1-5)...")
                self.local_image_pipe = StableDiffusionPipeline.from_pretrained(
                    "runwayml/stable-diffusion-v1-5",
                    safety_checker=None,
                    requires_safety_checker=False,
                )
                self.local_image_pipe = self.local_image_pipe.to("cpu")
                self.local_image_pipe.set_progress_bar_config(disable=True)

            gen_width = max(512, min(768, (width // 8) * 8))
            gen_height = max(512, min(768, (height // 8) * 8))
            negative_prompt = (
                "blurry, low quality, watermark, logo, gibberish text, distorted face, "
                "extra fingers, deformed hands, oversmoothed skin, cartoon, CGI"
            )

            image = self.local_image_pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=35,
                guidance_scale=8.5,
                width=gen_width,
                height=gen_height,
            ).images[0]

            if image.size != (width, height):
                image = image.resize((width, height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()

        return await loop.run_in_executor(None, _run_local)

    def diagnostics(self) -> dict[str, str]:
        return {
            "text_model": settings.caption_model_id,
            "image_model": settings.image_model_id,
            "text_model_loaded": "yes" if self.text_model is not None else "no",
            "last_text_model_used": self.last_text_model_used or "unknown",
            "last_image_model_used": self.last_image_model_used or "unknown",
            "last_image_source": self.last_image_source,
            "last_issue": self.last_issue or "none",
            "is_configured": "yes" if self.is_configured else "no",
            "image_mode": self._request_image_mode.get() or "online",
            "together_configured": "yes" if bool(self._effective_together_key()) else "no",
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

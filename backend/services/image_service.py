import hashlib
import io
import re
from typing import Literal

from PIL import Image, ImageStat

from core.config import settings
from core.huggingface_client import hf_client
from utils.file_storage import save_image_bytes


SizeType = Literal["1:1", "4:5", "16:9"]

SIZE_TO_DIMENSIONS: dict[SizeType, tuple[int, int]] = {
    "1:1": (1344, 1344),
    "4:5": (1152, 1440),
    "16:9": (1536, 864),
}


def _focus_keywords(prompt: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", prompt.lower())
    stop = {
        "create", "visual", "social", "media", "advertisement", "image", "with", "from", "that",
        "this", "your", "brand", "premium", "quality", "realistic", "photorealistic", "high",
    }
    unique: list[str] = []
    seen: set[str] = set()
    for w in words:
        if len(w) < 4 or w in stop:
            continue
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique[:5]


def _strip_text_overlay_instructions(prompt: str) -> str:
    cleaned = re.sub(r"(?is)text\s*overlay\s*:.*?(?=\n\n|\n[A-Z][a-z]+:|$)", "", prompt)
    cleaned = re.sub(r"(?is)tagline\s*:.*?(?=\n\n|\n[A-Z][a-z]+:|$)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _looks_low_quality(image_bytes: bytes) -> bool:
    if len(image_bytes) < 60_000:
        return True
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        stat = ImageStat.Stat(image)
        mean = sum(stat.mean) / 3
        std = sum(stat.stddev) / 3
        # Typical blank-ish placeholder patterns: very bright and very low variance.
        return mean > 220 and std < 30
    except Exception:
        return True


async def generate_images(prompt: str, size: SizeType, num_images: int) -> list[str]:
    width, height = SIZE_TO_DIMENSIONS[size]
    model_id = settings.image_model_id
    base_prompt = _strip_text_overlay_instructions(prompt)

    shot_styles = [
        "wide environmental lifestyle shot, subject occupies about 35% of frame",
        "three-quarter angle commercial shot with layered foreground and background elements",
        "editorial storytelling shot with natural scene context and depth",
        "balanced product-in-environment shot, not centered portrait crop",
    ]

    keywords = _focus_keywords(base_prompt)
    keyword_hint = ", ".join(keywords) if keywords else "main subject"
    seen_hashes: set[str] = set()

    async def _generate_one(index: int) -> str:
        shot_style = shot_styles[index % len(shot_styles)]
        for attempt in range(3):
            extra = ""
            if attempt == 1:
                extra = " editorial realism, authentic lighting falloff, realistic imperfections."
            elif attempt == 2:
                extra = " cinematic realism, richer local contrast, more texture definition."

            detailed_prompt = (
                f"{base_prompt}. {shot_style}, true-to-life textures, accurate proportions, "
                f"focus on key details: {keyword_hint}. "
                "natural reflections and shadows, high micro-detail, no blur, no washed colors, "
                "sharp subject isolation, crisp edge definition, realistic materials and fine grain detail, "
                "premium commercial advertising quality. Keep composition natural and believable. "
                "Avoid gibberish text, avoid watermark, avoid logo artifacts, avoid plastic-looking skin/materials, "
                "avoid over-smoothed AI look, avoid centered portrait-only framing. No text in image."
                f"{extra}"
            )
            content = await hf_client.generate_image(
                prompt=detailed_prompt,
                model_id=model_id,
                width=width,
                height=height,
            )

            digest = hashlib.sha256(content).hexdigest()
            if digest in seen_hashes:
                continue
            if _looks_low_quality(content):
                continue

            seen_hashes.add(digest)
            return save_image_bytes(content)

        # Last attempt fallback save so request still returns something.
        return save_image_bytes(content)

    # Run sequentially for steadier quality and provider stability.
    images: list[str] = []
    for i in range(num_images):
        images.append(await _generate_one(i))
    return images

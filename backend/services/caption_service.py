import re

from core.config import settings
from core.huggingface_client import hf_client


def _extract_hashtags(text: str) -> list[str]:
    tags = re.findall(r"#\w+", text)
    unique_tags: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = tag.lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_tags.append(tag)
    return unique_tags[:12]


async def generate_caption(prompt: str) -> tuple[str, list[str]]:
    instruction = (
        "Create one engaging social media caption (under 280 characters) and relevant hashtags. "
        "The caption should be compelling and marketing-focused.\n\n"
        f"Topic: {prompt}\n\n"
        "Output format: Caption first, then hashtags at the end."
    )
    generated = await hf_client.generate_text(
        instruction,
        model_id=settings.caption_model_id,
        max_new_tokens=150
    )
    hashtags = _extract_hashtags(generated)

    if not hashtags:
        hashtags = ["#marketing", "#socialmedia", "#content", "#brand", "#creative"]

    caption = generated
    for tag in hashtags:
        caption = caption.replace(tag, "")
    caption = " ".join(caption.split()).strip(" -\n\t")

    if not caption:
        caption = "Check out our latest content! #viral"

    return caption, hashtags

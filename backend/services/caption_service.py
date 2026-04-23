import re

from core.config import settings
from core.huggingface_client import hf_client


STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "from", "that", "this", "into", "your", "you",
    "are", "was", "were", "has", "have", "had", "about", "under", "over", "while", "through",
    "high", "quality", "ultra", "detailed", "photorealistic", "realistic", "image", "visual",
    "social", "media", "marketing", "brand", "campaign", "style", "clean", "premium"
}

GENERIC_HASHTAG_WORDS = {
    "create", "visual", "visually", "stunning", "advertisement", "photo", "image",
    "creative", "content", "post", "campaign", "marketing", "socialmedia", "social",
}


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


def _sanitize_tag(tag: str) -> str:
    base = tag.lower().lstrip("#")
    base = re.sub(r"[^a-z0-9]", "", base)
    return base


def _is_generic_tag(tag: str) -> bool:
    base = _sanitize_tag(tag)
    return not base or base in GENERIC_HASHTAG_WORDS


def _keywords_from_prompt(prompt: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", prompt.lower())
    filtered: list[str] = []
    seen: set[str] = set()
    for w in words:
        if len(w) < 4 or w in STOPWORDS:
            continue
        if w not in seen:
            seen.add(w)
            filtered.append(w)
    return filtered[:6]


def _extract_brand_name(prompt: str) -> str:
    brand_match = re.search(r"([A-Z][\w&'-]+(?:\s+[A-Z][\w&'-]+){0,3}\s*(?:Café|Cafe))", prompt)
    if brand_match:
        return brand_match.group(1).strip()
    fallback = re.search(r"([A-Z][\w&'-]+(?:\s+[A-Z][\w&'-]+){1,3})", prompt)
    return fallback.group(1).strip() if fallback else "your brand"


def _fallback_caption(prompt: str) -> str:
    brand = _extract_brand_name(prompt)
    lowered = prompt.lower()
    subject = "signature product"
    if "latte" in lowered:
        subject = "artisanal latte"
    elif "coffee" in lowered:
        subject = "premium coffee experience"
    elif "pizza" in lowered:
        subject = "freshly baked pizza"
    return (
        f"Slow down and savor {subject} at {brand} - crafted for warm, premium, story-driven moments your audience will remember."
    )


def _looks_like_prompt_echo(text: str) -> bool:
    lowered = text.lower()
    return (
        lowered.startswith("create ")
        or "social media advertisement" in lowered
        or "tagline:" in lowered
        or len(text.split()) > 45
    )


def _build_subject_hashtags(prompt: str, generated: str) -> list[str]:
    extracted = _extract_hashtags(generated)
    keywords = _keywords_from_prompt(prompt)
    subject_tags = [f"#{k}" for k in keywords]
    merged = subject_tags + extracted + ["#digitalmarketing", "#socialmediacampaign"]

    unique_tags: list[str] = []
    seen: set[str] = set()
    for tag in merged:
        if _is_generic_tag(tag):
            continue
        normalized = tag.lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_tags.append(tag)
    return unique_tags[:10]


async def generate_caption(prompt: str) -> tuple[str, list[str]]:
    instruction = (
        "Write one engaging social media caption under 180 characters for the exact subject provided. "
        "Mention clear subject cues from the prompt and keep it ad-ready, natural, and conversion-focused. "
        "Do not repeat the whole prompt. Do not output instructions.\n\n"
        f"Topic: {prompt}\n\n"
        "Output format:\nCaption: <single sentence>\nHashtags: <space-separated hashtags>"
    )
    generated = await hf_client.generate_text(
        instruction,
        model_id=settings.caption_model_id,
        max_new_tokens=150
    )
    hashtags = _build_subject_hashtags(prompt, generated)

    if not hashtags:
        hashtags = ["#digitalads", "#brandstorytelling", "#productmarketing"]

    caption_match = re.search(r"Caption:\s*(.+)", generated, flags=re.IGNORECASE)
    caption = caption_match.group(1).strip() if caption_match else generated
    for tag in hashtags:
        caption = caption.replace(tag, "")
    caption = " ".join(caption.split()).strip(" -\n\t")

    if not caption or _looks_like_prompt_echo(caption):
        caption = _fallback_caption(prompt)

    if len(caption) > 180:
        caption = caption[:177].rstrip() + "..."

    return caption, hashtags

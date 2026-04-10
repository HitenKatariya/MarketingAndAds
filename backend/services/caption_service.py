import re

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
        "Create one engaging social media caption (max 280 chars) and relevant hashtags. "
        "Output as plain text with hashtags included at the end. "
        f"Topic: {prompt}"
    )
    generated = await hf_client.generate_text(instruction, max_new_tokens=130)
    hashtags = _extract_hashtags(generated)

    if not hashtags:
        hashtags = ["#marketing", "#smallbusiness", "#branding"]

    caption = generated
    for tag in hashtags:
        caption = caption.replace(tag, "")
    caption = " ".join(caption.split()).strip(" -\n\t")

    if not caption:
        caption = "Fresh content crafted for your brand."

    return caption, hashtags

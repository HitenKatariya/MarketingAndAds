from core.config import settings
from core.huggingface_client import hf_client


def _is_human_subject(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "woman", "man", "girl", "boy", "person", "face", "portrait",
        "actress", "model", "fashion", "human", "people",
    ]
    return any(m in lowered for m in markers)


def _strong_prompt_fallback(user_idea: str) -> str:
    idea = " ".join(user_idea.split()).strip(" .")
    human_quality = (
        " Natural facial anatomy, realistic skin pores, accurate eyes and hands, no waxy skin, "
        "no distorted fingers, no deformed limbs."
        if _is_human_subject(idea)
        else ""
    )
    return (
        f"Commercial social media advertising image focused on {idea}. "
        "Hero composition, realistic product details, premium textures, balanced depth of field, "
        "cinematic key light with natural fill and soft shadow control, clean brand-safe art direction, "
        "high-end campaign styling, ultra-detailed, photorealistic, 8k quality."
        f"{human_quality}"
    )


def _looks_like_instruction_echo(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "you are a marketing expert",
        "transform this idea",
        "user idea:",
        "enhanced prompt:",
    ]
    return any(marker in lowered for marker in markers)


def _is_too_generic(text: str) -> bool:
    return len(text.split()) < 12


def _quality_suffix() -> str:
    return (
        " Photorealistic commercial quality, natural skin/material texture, crisp focus on subject, "
        "clean background separation, accurate lighting physics, high dynamic range, ultra-detailed. "
        "No gibberish text, no watermark, no logo artifacts."
    )


async def enhance_prompt(prompt: str) -> str:
    human_block = (
        "If the subject includes people or actress/model concepts, enforce natural facial symmetry, "
        "realistic skin texture, anatomically correct hands/fingers, and avoid doll-like AI faces.\n\n"
        if _is_human_subject(prompt)
        else ""
    )
    instruction = (
        "You are a marketing expert. Transform this idea into a detailed, marketing-grade visual prompt "
        "for AI image generation. Include composition, lighting, mood, realism, and brand-friendly tone. "
        "Be specific and descriptive. Do not output instruction-like text.\n\n"
        f"{human_block}"
        f"User idea: {prompt}\n\n"
        "Enhanced prompt:"
    )
    enhanced = await hf_client.generate_text(
        instruction,
        model_id=settings.prompt_model_id,
        max_new_tokens=200
    )
    cleaned = enhanced.strip().strip('"').strip("'")

    # If model echoes the instruction template, force a clean usable prompt.
    if _looks_like_instruction_echo(cleaned):
        return _strong_prompt_fallback(prompt)

    if not cleaned or _is_too_generic(cleaned):
        return _strong_prompt_fallback(prompt)

    # Ensure all successful prompts keep a minimum quality/detail baseline.
    return f"{cleaned.rstrip('.')}." + _quality_suffix()

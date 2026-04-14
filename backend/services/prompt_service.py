from core.config import settings
from core.huggingface_client import hf_client


async def enhance_prompt(prompt: str) -> str:
    instruction = (
        "You are a marketing expert. Transform this idea into a detailed, marketing-grade visual prompt "
        "for AI image generation. Include composition, lighting, mood, realism, and brand-friendly tone. "
        "Be specific and descriptive.\n\n"
        f"User idea: {prompt}\n\n"
        "Enhanced prompt:"
    )
    enhanced = await hf_client.generate_text(
        instruction,
        model_id=settings.prompt_model_id,
        max_new_tokens=200
    )
    return enhanced.strip().strip('"').strip("'")

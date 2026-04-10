from core.huggingface_client import hf_client


async def enhance_prompt(prompt: str) -> str:
    instruction = (
        "Rewrite this idea as a concise marketing-grade visual prompt for image generation. "
        "Include composition, lighting, mood, realism, and brand-friendly tone. "
        f"User idea: {prompt}"
    )
    enhanced = await hf_client.generate_text(instruction, max_new_tokens=120)
    return enhanced.strip().strip('"')

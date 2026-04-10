import asyncio
from typing import Literal

from core.huggingface_client import hf_client
from utils.file_storage import save_image_bytes


SizeType = Literal["1:1", "4:5", "16:9"]

SIZE_TO_DIMENSIONS: dict[SizeType, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "4:5": (1024, 1280),
    "16:9": (1280, 720),
}


async def generate_images(prompt: str, size: SizeType, num_images: int) -> list[str]:
    width, height = SIZE_TO_DIMENSIONS[size]

    async def _generate_one(index: int) -> str:
        content = await hf_client.generate_image(
            prompt=f"{prompt}. Variation {index + 1}",
            width=width,
            height=height,
        )
        return save_image_bytes(content)

    tasks = [_generate_one(i) for i in range(num_images)]
    return await asyncio.gather(*tasks)

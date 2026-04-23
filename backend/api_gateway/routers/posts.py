from fastapi import APIRouter, HTTPException

from models.schemas import (
    CaptionRequest,
    CaptionResponse,
    DeleteResponse,
    EnhancedPromptRequest,
    EnhancedPromptResponse,
    GenerateImagesRequest,
    GenerateImagesResponse,
    GeneratePostRequest,
    GeneratePostResponse,
    GenerateTextRequest,
    HistoryItem,
    SaveGenerationRequest,
)
from services.caption_service import generate_caption
from services.image_service import generate_images
from services.prompt_service import enhance_prompt
from utils.file_storage import delete_generation, list_history, save_generation_metadata


router = APIRouter(tags=["Post Generator"])


@router.post("/enhance-prompt", response_model=EnhancedPromptResponse)
async def enhance_prompt_endpoint(payload: EnhancedPromptRequest) -> EnhancedPromptResponse:
    enhanced = await enhance_prompt(payload.prompt)
    return EnhancedPromptResponse(enhanced_prompt=enhanced)


@router.post("/generate-caption", response_model=CaptionResponse)
async def generate_caption_endpoint(payload: CaptionRequest) -> CaptionResponse:
    caption, hashtags = await generate_caption(payload.prompt)
    return CaptionResponse(caption=caption, hashtags=hashtags)


@router.post("/generate-images", response_model=GenerateImagesResponse)
async def generate_images_endpoint(payload: GenerateImagesRequest) -> GenerateImagesResponse:
    try:
        images = await generate_images(
            prompt=payload.prompt,
            size=payload.size,
            num_images=payload.num_images,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateImagesResponse(images=images)


@router.post("/generate-post", response_model=GeneratePostResponse)
async def generate_post_endpoint(payload: GeneratePostRequest) -> GeneratePostResponse:
    enhanced = await enhance_prompt(payload.prompt)
    caption, hashtags = await generate_caption(enhanced)
    try:
        images = await generate_images(
            prompt=enhanced,
            size=payload.size,
            num_images=payload.num_images,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    saved = save_generation_metadata(
        prompt=payload.prompt,
        enhanced_prompt=enhanced,
        caption=caption,
        hashtags=hashtags,
        images=images,
    )

    return GeneratePostResponse(
        id=saved.id,
        prompt=saved.prompt,
        enhanced_prompt=saved.enhanced_prompt,
        caption=saved.caption,
        hashtags=saved.hashtags,
        images=saved.images,
        created_at=saved.created_at,
    )


@router.post("/generate-text", response_model=GeneratePostResponse)
async def generate_text_endpoint(payload: GenerateTextRequest) -> GeneratePostResponse:
    enhanced = await enhance_prompt(payload.prompt) if payload.use_enhancement else payload.prompt
    caption, hashtags = await generate_caption(enhanced)

    saved = save_generation_metadata(
        prompt=payload.prompt,
        enhanced_prompt=enhanced,
        caption=caption,
        hashtags=hashtags,
        images=[],
    )

    return GeneratePostResponse(
        id=saved.id,
        prompt=saved.prompt,
        enhanced_prompt=saved.enhanced_prompt,
        caption=saved.caption,
        hashtags=saved.hashtags,
        images=saved.images,
        created_at=saved.created_at,
    )


@router.post("/save-generation", response_model=GeneratePostResponse)
async def save_generation_endpoint(payload: SaveGenerationRequest) -> GeneratePostResponse:
    saved = save_generation_metadata(
        prompt=payload.prompt,
        enhanced_prompt=payload.enhanced_prompt,
        caption=payload.caption,
        hashtags=payload.hashtags,
        images=payload.images,
    )
    return GeneratePostResponse(
        id=saved.id,
        prompt=saved.prompt,
        enhanced_prompt=saved.enhanced_prompt,
        caption=saved.caption,
        hashtags=saved.hashtags,
        images=saved.images,
        created_at=saved.created_at,
    )


@router.get("/history", response_model=list[HistoryItem])
async def history_endpoint() -> list[HistoryItem]:
    return list_history()


@router.delete("/delete/{generation_id}", response_model=DeleteResponse)
async def delete_endpoint(generation_id: str) -> DeleteResponse:
    deleted = delete_generation(generation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Generation not found")
    return DeleteResponse(message=f"Deleted generation {generation_id}")

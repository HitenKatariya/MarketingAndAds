from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PostSize = Literal["1:1", "4:5", "16:9"]
PROMPT_MAX_LENGTH = 12000


class EnhancedPromptRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)


class EnhancedPromptResponse(BaseModel):
    enhanced_prompt: str


class CaptionRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)


class CaptionResponse(BaseModel):
    caption: str
    hashtags: list[str]


class GenerateImagesRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)
    size: PostSize = "1:1"
    num_images: int = Field(default=3, ge=1, le=4)


class GenerateImagesResponse(BaseModel):
    images: list[str]


class GeneratePostRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)
    size: PostSize = "1:1"
    num_images: int = Field(default=3, ge=1, le=4)


class GenerateTextRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)
    use_enhancement: bool = True


class SaveGenerationRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)
    enhanced_prompt: str = Field(min_length=5, max_length=PROMPT_MAX_LENGTH)
    caption: str = Field(min_length=1, max_length=PROMPT_MAX_LENGTH)
    hashtags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)


class HistoryItem(BaseModel):
    id: str
    prompt: str
    enhanced_prompt: str
    caption: str
    hashtags: list[str]
    images: list[str]
    created_at: datetime


class GeneratePostResponse(HistoryItem):
    pass


class DeleteResponse(BaseModel):
    message: str

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PostSize = Literal["1:1", "4:5", "16:9"]


class EnhancedPromptRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=500)


class EnhancedPromptResponse(BaseModel):
    enhanced_prompt: str


class CaptionRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=500)


class CaptionResponse(BaseModel):
    caption: str
    hashtags: list[str]


class GenerateImagesRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=500)
    size: PostSize = "1:1"
    num_images: int = Field(default=3, ge=1, le=4)


class GenerateImagesResponse(BaseModel):
    images: list[str]


class GeneratePostRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=500)
    size: PostSize = "1:1"
    num_images: int = Field(default=3, ge=1, le=4)


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

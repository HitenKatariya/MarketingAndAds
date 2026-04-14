from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "ai-post-generator"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    request_timeout_seconds: int = 60
    hf_inference_base_url: str = "https://router.huggingface.co/hf-inference/models"

    huggingface_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HUGGINGFACE_API_KEY",
            "HF_TOKENS",
            "HF_TOKEN",
            "huggingface_api_key",
        ),
    )
    text_model_id: str = "google/flan-t5-large"
    image_model_id: str = "runwayml/stable-diffusion-v1-5"

    outputs_dir: Path = BASE_DIR / "outputs"
    images_dir: Path = BASE_DIR / "outputs" / "images"
    json_dir: Path = BASE_DIR / "outputs" / "json"

    allowed_origins: list[str] = ["*"]


settings = Settings()

settings.outputs_dir.mkdir(parents=True, exist_ok=True)
settings.images_dir.mkdir(parents=True, exist_ok=True)
settings.json_dir.mkdir(parents=True, exist_ok=True)


def backend_mode() -> str:
    return "online" if settings.huggingface_api_key.strip() else "offline"

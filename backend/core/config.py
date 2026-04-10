from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")

    app_env: str = "development"
    app_name: str = "ai-post-generator"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    request_timeout_seconds: int = 60

    huggingface_api_key: str = ""
    text_model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"
    image_model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"

    outputs_dir: Path = BASE_DIR / "outputs"
    images_dir: Path = BASE_DIR / "outputs" / "images"
    json_dir: Path = BASE_DIR / "outputs" / "json"

    allowed_origins: list[str] = ["*"]


settings = Settings()

settings.outputs_dir.mkdir(parents=True, exist_ok=True)
settings.images_dir.mkdir(parents=True, exist_ok=True)
settings.json_dir.mkdir(parents=True, exist_ok=True)

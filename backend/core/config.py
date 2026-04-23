from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file() -> dict[str, str]:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return {}
    result = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


_env_vars = _load_env_file()


def _get_hf_key() -> str:
    for key in ["huggingface_api_key", "HF_TOKENS", "HF_TOKEN", "HUGGINGFACE_API_KEY"]:
        val = _env_vars.get(key, os.environ.get(key, "")).strip()
        if val:
            return val
    return ""


def _get_together_key() -> str:
    for key in ["together_api_key", "TOGETHER_API_KEY"]:
        val = _env_vars.get(key, os.environ.get(key, "")).strip()
        if val:
            return val
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_name: str = "ai-post-generator"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    request_timeout_seconds: int = 300

    huggingface_api_key: str = ""
    together_api_key: str = ""
    prompt_model_id: str = "mistralai/Mistral-7B-Instruct-v0.3"
    caption_model_id: str = "google/flan-t5-base"
    hashtag_model_id: str = "jjae/hashtag"
    image_model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"
    together_text_model_id: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    together_image_model_id: str = "black-forest-labs/FLUX.1-schnell"

    outputs_dir: Path = BASE_DIR / "outputs"
    images_dir: Path = BASE_DIR / "outputs" / "images"
    json_dir: Path = BASE_DIR / "outputs" / "json"

    allowed_origins: list[str] = ["*", "http://localhost:5173", "http://localhost:3000"]

    @property
    def hf_api_key(self) -> str:
        return _get_hf_key()


settings = Settings()

settings.outputs_dir.mkdir(parents=True, exist_ok=True)
settings.images_dir.mkdir(parents=True, exist_ok=True)
settings.json_dir.mkdir(parents=True, exist_ok=True)


def backend_mode() -> str:
    return "online" if (_get_hf_key() or _get_together_key()) else "offline"


def get_hf_api_key() -> str:
    return _get_hf_key()


def get_together_api_key() -> str:
    return _get_together_key()

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.config import settings
from models.schemas import HistoryItem


def _image_relative_path(file_name: str) -> str:
    return str(Path("outputs") / "images" / file_name).replace("\\", "/")


def save_image_bytes(image_bytes: bytes) -> str:
    file_name = f"{uuid4().hex}.png"
    destination = settings.images_dir / file_name
    destination.write_bytes(image_bytes)
    return _image_relative_path(file_name)


def save_generation_metadata(
    *,
    prompt: str,
    enhanced_prompt: str,
    caption: str,
    hashtags: list[str],
    images: list[str],
) -> HistoryItem:
    generation_id = uuid4().hex
    created_at = datetime.now(UTC)
    payload = {
        "id": generation_id,
        "prompt": prompt,
        "enhanced_prompt": enhanced_prompt,
        "caption": caption,
        "hashtags": hashtags,
        "images": images,
        "created_at": created_at.isoformat(),
    }

    (settings.json_dir / f"{generation_id}.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return HistoryItem(
        id=generation_id,
        prompt=prompt,
        enhanced_prompt=enhanced_prompt,
        caption=caption,
        hashtags=hashtags,
        images=images,
        created_at=created_at,
    )


def list_history() -> list[HistoryItem]:
    items: list[HistoryItem] = []
    for file_path in sorted(settings.json_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            items.append(HistoryItem.model_validate(data))
        except Exception:
            continue
    return items


def delete_generation(generation_id: str) -> bool:
    meta_file = settings.json_dir / f"{generation_id}.json"
    if not meta_file.exists():
        return False

    data = json.loads(meta_file.read_text(encoding="utf-8"))
    for image_path in data.get("images", []):
        img_abs = settings.outputs_dir.parent / image_path
        if img_abs.exists():
            img_abs.unlink(missing_ok=True)

    meta_file.unlink(missing_ok=True)
    return True

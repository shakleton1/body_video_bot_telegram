import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class MenuMode:
    id: str
    name: str


@dataclass(frozen=True)
class MenuSection:
    id: str
    name: str
    modes: List[MenuMode]


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    menu_path: Path
    videos_path: Path


def _parse_admin_ids(value: str | None) -> set[int]:
    if not value:
        return set()
    ids: set[int] = set()
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError as exc:
            raise ValueError(f"ADMIN_IDS contains a non-integer value: {chunk}") from exc
    return ids


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS"))

    base_dir = Path(__file__).resolve().parent.parent
    menu_path = base_dir / "data" / "menu.json"
    videos_path = base_dir / "data" / "videos.json"

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        menu_path=menu_path,
        videos_path=videos_path,
    )

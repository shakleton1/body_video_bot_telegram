import asyncio
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

from ..config import MenuSection


class VideoStorage:
    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._data: Dict[str, Dict[str, Optional[str]]] = {}
        self._lock = asyncio.Lock()

    async def load(self, menu: Iterable[MenuSection]) -> None:
        async with self._lock:
            if self._path.exists():
                with self._path.open("r", encoding="utf-8") as f:
                    raw: Dict[str, Dict[str, Optional[str]]] = json.load(f)
                self._data = raw
            else:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._data = self._make_default_data(menu)
                await self._write_locked()

            if self._merge_with_defaults(menu):
                await self._write_locked()

    async def get_video(self, category: str, mode: str) -> Optional[str]:
        async with self._lock:
            return self._data.get(category, {}).get(mode)

    async def set_video(self, category: str, mode: str, file_id: str) -> None:
        async with self._lock:
            if category not in self._data:
                raise KeyError(f"Unknown category: {category}")
            if mode not in self._data[category]:
                raise KeyError(f"Unknown mode '{mode}' for category '{category}'")

            self._data[category][mode] = file_id
            await self._write_locked()

    def _make_default_data(self, menu: Iterable[MenuSection]) -> Dict[str, Dict[str, Optional[str]]]:
        return {
            section.name: {mode.name: None for mode in section.modes}
            for section in menu
        }

    def _merge_with_defaults(self, menu: Iterable[MenuSection]) -> bool:
        defaults = self._make_default_data(menu)
        changed = False
        for category, modes in defaults.items():
            if category not in self._data:
                changed = True
            stored = self._data.setdefault(category, {})
            for mode, default_value in modes.items():
                if mode not in stored:
                    stored[mode] = default_value
                    changed = True

        # Drop obsolete categories/modes if menu changed
        to_remove = [category for category in self._data if category not in defaults]
        for category in to_remove:
            self._data.pop(category, None)
            changed = True
        for category, modes in list(self._data.items()):
            valid_modes = defaults[category]
            obsolete_modes = [mode for mode in modes if mode not in valid_modes]
            for mode in obsolete_modes:
                modes.pop(mode, None)
                changed = True

        return changed

    async def add_section(self, section: MenuSection) -> None:
        async with self._lock:
            self._data.setdefault(
                section.name, {mode.name: None for mode in section.modes}
            )
            await self._write_locked()

    async def rename_section(self, old_name: str, new_name: str) -> None:
        async with self._lock:
            if old_name not in self._data:
                return
            if new_name in self._data and new_name != old_name:
                raise ValueError("Target section name already exists")
            self._data[new_name] = self._data.pop(old_name)
            await self._write_locked()

    async def delete_section(self, section_name: str) -> None:
        async with self._lock:
            if section_name in self._data:
                self._data.pop(section_name, None)
                await self._write_locked()

    async def add_mode(self, section_name: str, mode_name: str) -> None:
        async with self._lock:
            section = self._data.setdefault(section_name, {})
            if mode_name not in section:
                section[mode_name] = None
                await self._write_locked()

    async def rename_mode(self, section_name: str, old_mode: str, new_mode: str) -> None:
        async with self._lock:
            section = self._data.get(section_name)
            if not section or old_mode not in section:
                return
            if new_mode in section and new_mode != old_mode:
                raise ValueError("Target mode name already exists")
            section[new_mode] = section.pop(old_mode)
            await self._write_locked()

    async def delete_mode(self, section_name: str, mode_name: str) -> None:
        async with self._lock:
            section = self._data.get(section_name)
            if section and mode_name in section:
                section.pop(mode_name, None)
                await self._write_locked()

    async def _write_locked(self) -> None:
        serialized = json.dumps(self._data, ensure_ascii=False, indent=2)
        await asyncio.to_thread(self._path.write_text, serialized, encoding="utf-8")

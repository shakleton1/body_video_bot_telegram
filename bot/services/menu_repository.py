import asyncio
import json
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from uuid import uuid4

from ..config import MenuMode, MenuSection


class MenuRepository:
    def __init__(self, menu_path: Path) -> None:
        self._path = menu_path
        self._sections: List[MenuSection] = []
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        async with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._sections = []
                await self._write_locked()
                return

            content = await asyncio.to_thread(self._path.read_text, encoding="utf-8")
            data = json.loads(content)
            sections, needs_save = self._deserialize(data)
            self._sections = sections
            if needs_save:
                await self._write_locked()

    async def get_sections(self) -> List[MenuSection]:
        async with self._lock:
            return [self._clone_section(section) for section in self._sections]

    async def get_section(self, section_id: str) -> Optional[MenuSection]:
        async with self._lock:
            section = self._find_section(section_id)
            return self._clone_section(section) if section else None

    async def get_mode(self, section_id: str, mode_id: str) -> Optional[Tuple[MenuSection, MenuMode]]:
        async with self._lock:
            section = self._find_section(section_id)
            if not section:
                return None
            for mode in section.modes:
                if mode.id == mode_id:
                    return self._clone_section(section), mode
            return None

    async def add_section(self, name: str) -> MenuSection:
        async with self._lock:
            section = MenuSection(id=self._generate_section_id(), name=name, modes=[])
            self._sections.append(section)
            await self._write_locked()
            return self._clone_section(section)

    async def rename_section(self, section_id: str, new_name: str) -> MenuSection:
        async with self._lock:
            index = self._index_section(section_id)
            if index is None:
                raise KeyError(f"Section '{section_id}' not found")
            section = self._sections[index]
            updated = MenuSection(id=section.id, name=new_name, modes=list(section.modes))
            self._sections[index] = updated
            await self._write_locked()
            return self._clone_section(updated)

    async def delete_section(self, section_id: str) -> MenuSection:
        async with self._lock:
            index = self._index_section(section_id)
            if index is None:
                raise KeyError(f"Section '{section_id}' not found")
            section = self._sections.pop(index)
            await self._write_locked()
            return section

    async def add_mode(self, section_id: str, name: str) -> Tuple[MenuSection, MenuMode]:
        async with self._lock:
            index = self._index_section(section_id)
            if index is None:
                raise KeyError(f"Section '{section_id}' not found")

            section = self._sections[index]
            new_mode = MenuMode(id=self._generate_mode_id(section), name=name)
            updated_modes = list(section.modes) + [new_mode]
            updated_section = MenuSection(id=section.id, name=section.name, modes=updated_modes)
            self._sections[index] = updated_section
            await self._write_locked()
            return self._clone_section(updated_section), new_mode

    async def rename_mode(self, section_id: str, mode_id: str, new_name: str) -> Tuple[MenuSection, MenuMode]:
        async with self._lock:
            index = self._index_section(section_id)
            if index is None:
                raise KeyError(f"Section '{section_id}' not found")

            section = self._sections[index]
            updated_modes: List[MenuMode] = []
            target_mode: Optional[MenuMode] = None
            for mode in section.modes:
                if mode.id == mode_id:
                    target_mode = MenuMode(id=mode.id, name=new_name)
                    updated_modes.append(target_mode)
                else:
                    updated_modes.append(mode)

            if target_mode is None:
                raise KeyError(f"Mode '{mode_id}' not found in section '{section_id}'")

            updated_section = MenuSection(id=section.id, name=section.name, modes=updated_modes)
            self._sections[index] = updated_section
            await self._write_locked()
            return self._clone_section(updated_section), target_mode

    async def delete_mode(self, section_id: str, mode_id: str) -> Tuple[MenuSection, MenuMode]:
        async with self._lock:
            index = self._index_section(section_id)
            if index is None:
                raise KeyError(f"Section '{section_id}' not found")

            section = self._sections[index]
            remaining_modes: List[MenuMode] = []
            deleted_mode: Optional[MenuMode] = None
            for mode in section.modes:
                if mode.id == mode_id:
                    deleted_mode = mode
                else:
                    remaining_modes.append(mode)

            if deleted_mode is None:
                raise KeyError(f"Mode '{mode_id}' not found in section '{section_id}'")

            updated_section = MenuSection(id=section.id, name=section.name, modes=remaining_modes)
            self._sections[index] = updated_section
            await self._write_locked()
            return self._clone_section(updated_section), deleted_mode

    def _deserialize(self, raw_data) -> Tuple[List[MenuSection], bool]:
        if not isinstance(raw_data, list):
            raise ValueError("Menu file must contain a list")

        sections: List[MenuSection] = []
        used_section_ids: set[str] = set()
        used_mode_ids: set[str] = set()
        needs_save = False

        for entry in raw_data:
            if isinstance(entry, dict):
                name = entry.get("name")
                if not isinstance(name, str):
                    raise ValueError("Section name must be a string")
                section_id = entry.get("id")
                if not isinstance(section_id, str):
                    section_id = self._generate_section_id(used_section_ids)
                    needs_save = True
                if section_id in used_section_ids:
                    section_id = self._generate_section_id(used_section_ids)
                    needs_save = True
                used_section_ids.add(section_id)

                modes_raw = entry.get("modes", [])
                modes: List[MenuMode] = []
                if isinstance(modes_raw, list):
                    for mode_entry in modes_raw:
                        if isinstance(mode_entry, dict):
                            mode_name = mode_entry.get("name")
                            if not isinstance(mode_name, str):
                                raise ValueError("Mode name must be a string")
                            mode_id = mode_entry.get("id")
                            if not isinstance(mode_id, str) or mode_id in used_mode_ids:
                                mode_id = self._generate_mode_id(None, used_mode_ids)
                                needs_save = True
                            used_mode_ids.add(mode_id)
                            modes.append(MenuMode(id=mode_id, name=mode_name))
                        elif isinstance(mode_entry, str):
                            mode_id = self._generate_mode_id(None, used_mode_ids)
                            used_mode_ids.add(mode_id)
                            modes.append(MenuMode(id=mode_id, name=mode_entry))
                            needs_save = True
                        else:
                            raise ValueError("Mode entry must be a dict or string")
                else:
                    raise ValueError("Section modes must be a list")

                sections.append(MenuSection(id=section_id, name=name, modes=modes))
            elif isinstance(entry, str):
                # Legacy format: list of section names without details
                section_id = self._generate_section_id(used_section_ids)
                used_section_ids.add(section_id)
                sections.append(MenuSection(id=section_id, name=entry, modes=[]))
                needs_save = True
            else:
                raise ValueError("Unsupported menu entry format")

        return sections, needs_save

    def _index_section(self, section_id: str) -> Optional[int]:
        for index, section in enumerate(self._sections):
            if section.id == section_id:
                return index
        return None

    def _find_section(self, section_id: str) -> Optional[MenuSection]:
        index = self._index_section(section_id)
        return self._sections[index] if index is not None else None

    def _generate_section_id(self, used: Optional[Iterable[str]] = None) -> str:
        used_ids = set(used or [])
        used_ids.update(section.id for section in self._sections)
        while True:
            candidate = f"s{uuid4().hex[:6]}"
            if candidate not in used_ids:
                return candidate

    def _generate_mode_id(
        self, section: Optional[MenuSection] = None, used: Optional[Iterable[str]] = None
    ) -> str:
        used_ids = set(used or [])
        if section:
            used_ids.update(mode.id for mode in section.modes)
        for current_section in self._sections:
            used_ids.update(mode.id for mode in current_section.modes)
        while True:
            candidate = f"m{uuid4().hex[:6]}"
            if candidate not in used_ids:
                return candidate

    async def _write_locked(self) -> None:
        serialized = json.dumps(self._serialize_sections(), ensure_ascii=False, indent=2)
        await asyncio.to_thread(self._path.write_text, serialized, encoding="utf-8")

    def _serialize_sections(self) -> List[dict]:
        return [
            {
                "id": section.id,
                "name": section.name,
                "modes": [
                    {"id": mode.id, "name": mode.name} for mode in section.modes
                ],
            }
            for section in self._sections
        ]

    @staticmethod
    def _clone_section(section: MenuSection) -> MenuSection:
        return MenuSection(id=section.id, name=section.name, modes=list(section.modes))

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from ..services.menu_repository import MenuRepository
from ..keyboards import (
    UserMenuCallback,
    build_main_menu,
    build_modes_menu,
)
from ..services.storage import VideoStorage


def create_user_router(menu_repo: MenuRepository, storage: VideoStorage) -> Router:
    router = Router(name="user")

    base_dir = Path(__file__).resolve().parent.parent

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        menu = await menu_repo.get_sections()
        if not menu:
            await message.answer(
                "Меню пока не настроено. Обратитесь к администратору.",
            )
            return

        await message.answer(
            "Выберите зону, которую хотите проработать:",
            reply_markup=build_main_menu(menu),
        )

    @router.callback_query(UserMenuCallback.filter(F.action == "category"))
    async def on_category(callback: CallbackQuery, callback_data: UserMenuCallback) -> None:
        section = await menu_repo.get_section(callback_data.section_id)
        if not section:
            await callback.answer("Раздел недоступен", show_alert=True)
            return

        await callback.message.edit_text(
            f"{section.name}: выберите режим занятий",
            reply_markup=build_modes_menu(section),
        )
        await callback.answer()

    @router.callback_query(UserMenuCallback.filter(F.action == "back"))
    async def on_back(callback: CallbackQuery) -> None:
        menu = await menu_repo.get_sections()
        if not menu:
            await callback.message.edit_text(
                "Меню пока не настроено. Обратитесь к администратору.",
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            "Выберите зону, которую хотите проработать:",
            reply_markup=build_main_menu(menu),
        )
        await callback.answer()

    @router.callback_query(UserMenuCallback.filter(F.action == "mode"))
    async def on_mode(callback: CallbackQuery, callback_data: UserMenuCallback) -> None:
        if not callback_data.mode_id:
            await callback.answer("Режим недоступен", show_alert=True)
            return

        result = await menu_repo.get_mode(callback_data.section_id, callback_data.mode_id)
        if not result:
            await callback.answer("Раздел недоступен", show_alert=True)
            return
        section, mode = result

        video_id = await storage.get_video(section.name, mode.name)

        if video_id:
            video_source = _resolve_video_reference(video_id, base_dir)
            message_sent = await callback.message.answer_video(
                video=video_source,
                caption=f"{section.name} · {mode.name}",
            )

            if isinstance(video_source, FSInputFile) and message_sent.video:
                await storage.set_video(section.name, mode.name, message_sent.video.file_id)
        else:
            await callback.message.answer(
                "Видео пока не добавлено. Обратитесь к администратору.",
            )

        await callback.answer()

    return router


def _resolve_video_reference(value: str, base_dir: Path) -> str | FSInputFile:
    lowered = value.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return value

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()

    if candidate.exists() and candidate.is_file():
        return FSInputFile(str(candidate))

    return value

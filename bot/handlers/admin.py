from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards import (
    AdminActions,
    AdminMenuCallback,
    build_admin_menu_mode,
    build_admin_menu_section,
    build_admin_menu_sections,
    build_admin_root_menu,
    build_admin_video_categories,
    build_admin_video_modes,
    build_confirmation_keyboard,
)
from ..services.menu_repository import MenuRepository
from ..services.storage import VideoStorage


class AdminStates(StatesGroup):
    choosing_action = State()
    choosing_category = State()
    choosing_mode = State()
    waiting_video = State()
    menu_sections = State()
    menu_section_detail = State()
    menu_mode_detail = State()
    menu_waiting_input = State()
    menu_confirm = State()


def create_admin_router(
    admin_ids: set[int], menu_repo: MenuRepository, storage: VideoStorage
) -> Router:
    router = Router(name="admin")

    def is_admin(user_id: int | None) -> bool:
        return bool(user_id and user_id in admin_ids)

    async def send_root_menu(message: Message | CallbackQuery) -> None:
        markup = build_admin_root_menu()
        text = "Выберите режим администрирования:"
        if isinstance(message, Message):
            await message.answer(text, reply_markup=markup)
        else:
            await message.message.edit_text(text, reply_markup=markup)

    @router.message(Command("admin"))
    async def admin_entry(message: Message, state: FSMContext) -> None:
        if not is_admin(message.from_user.id if message.from_user else None):
            await message.answer("Доступ запрещен")
            return

        await state.clear()
        await state.set_state(AdminStates.choosing_action)
        await send_root_menu(message)

    @router.message(Command("cancel"))
    async def cancel(message: Message, state: FSMContext) -> None:
        if not is_admin(message.from_user.id if message.from_user else None):
            return

        await state.clear()
        await message.answer("Настройка отменена.")

    @router.callback_query(AdminMenuCallback.filter())
    async def handle_callbacks(
        callback: CallbackQuery, callback_data: AdminMenuCallback, state: FSMContext
    ) -> None:
        if not is_admin(callback.from_user.id if callback.from_user else None):
            await callback.answer("Недостаточно прав", show_alert=True)
            return

        action = callback_data.action

        if action == AdminActions.VIDEO:
            menu = await menu_repo.get_sections()
            if not menu:
                await callback.answer("Меню пустое. Добавьте разделы в настройках меню.", show_alert=True)
                return
            await state.set_state(AdminStates.choosing_category)
            await callback.message.edit_text(
                "Выберите раздел для обновления видео:",
                reply_markup=build_admin_video_categories(menu),
            )
            await callback.answer()
            return

        if action == AdminActions.VIDEO_BACK:
            current_state = await state.get_state()
            if current_state == AdminStates.choosing_category.state:
                await state.set_state(AdminStates.choosing_action)
                await send_root_menu(callback)
            else:
                menu = await menu_repo.get_sections()
                await state.set_state(AdminStates.choosing_category)
                await callback.message.edit_text(
                    "Выберите раздел для обновления видео:",
                    reply_markup=build_admin_video_categories(menu),
                )
            await callback.answer()
            return

        if action == AdminActions.VIDEO_CATEGORY:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.update_data(video_section_id=section.id)
            await state.set_state(AdminStates.choosing_mode)
            await callback.message.edit_text(
                f"{section.name}: выберите режим для изменения видео",
                reply_markup=build_admin_video_modes(section),
            )
            await callback.answer()
            return

        if action == AdminActions.VIDEO_MODE:
            if not callback_data.mode_id:
                await callback.answer("Режим не найден", show_alert=True)
                return
            result = await menu_repo.get_mode(callback_data.section_id, callback_data.mode_id)
            if not result:
                await callback.answer("Режим не найден", show_alert=True)
                return
            section, mode = result
            await state.update_data(video_section_id=section.id, video_mode_id=mode.id)
            await state.set_state(AdminStates.waiting_video)
            current_video = await storage.get_video(section.name, mode.name)
            status = "установлено" if current_video else "не задано"
            await callback.message.edit_text(
                (
                    f"{section.name} · {mode.name}\n"
                    f"Текущее видео: {status}.\n"
                    "Отправьте новое видео сообщением, чтобы обновить его.\n"
                    "Для отмены используйте /cancel."
                ),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU:
            sections = await menu_repo.get_sections()
            await state.set_state(AdminStates.menu_sections)
            await callback.message.edit_text(
                "Управление меню. Выберите раздел:",
                reply_markup=build_admin_menu_sections(sections),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_BACK:
            await state.set_state(AdminStates.choosing_action)
            await send_root_menu(callback)
            await callback.answer()
            return

        if action == AdminActions.MENU_ADD_SECTION:
            await state.set_state(AdminStates.menu_waiting_input)
            await state.update_data(menu_task="add_section")
            await callback.message.edit_text(
                "Введите название нового раздела:",
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_SECTION_BACK:
            sections = await menu_repo.get_sections()
            await state.set_state(AdminStates.menu_sections)
            await callback.message.edit_text(
                "Управление меню. Выберите раздел:",
                reply_markup=build_admin_menu_sections(sections),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_SECTION:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.update_data(menu_section_id=section.id)
            await state.set_state(AdminStates.menu_section_detail)
            await callback.message.edit_text(
                f"Раздел «{section.name}». Выберите действие:",
                reply_markup=build_admin_menu_section(section),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_SECTION_RENAME:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.set_state(AdminStates.menu_waiting_input)
            await state.update_data(
                menu_task="rename_section",
                menu_section_id=section.id,
                previous_section_name=section.name,
            )
            await callback.message.edit_text(
                f"Введите новое название для раздела «{section.name}»:",
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_SECTION_DELETE:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.set_state(AdminStates.menu_confirm)
            await state.update_data(
                menu_task="delete_section",
                menu_section_id=section.id,
                menu_section_name=section.name,
            )
            await callback.message.edit_text(
                f"Удалить раздел «{section.name}» и все его режимы?",
                reply_markup=build_confirmation_keyboard(
                    AdminActions.MENU_SECTION_DELETE_CONFIRM,
                    AdminActions.MENU_SECTION_DELETE_CANCEL,
                    section.id,
                ),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_SECTION_DELETE_CONFIRM:
            data = await state.get_data()
            if data.get("menu_task") != "delete_section":
                await callback.answer("Операция уже отменена", show_alert=True)
                return
            try:
                section = await menu_repo.delete_section(callback_data.section_id)
            except KeyError:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await storage.delete_section(section.name)
            await state.set_state(AdminStates.menu_sections)
            await state.update_data(menu_task=None)
            sections = await menu_repo.get_sections()
            await callback.message.edit_text(
                "Раздел удален. Выберите дальнейшее действие:",
                reply_markup=build_admin_menu_sections(sections),
            )
            await callback.answer("Раздел удален")
            return

        if action == AdminActions.MENU_SECTION_DELETE_CANCEL:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.set_state(AdminStates.menu_section_detail)
            await state.update_data(menu_task=None)
            await callback.message.edit_text(
                f"Раздел «{section.name}». Выберите действие:",
                reply_markup=build_admin_menu_section(section),
            )
            await callback.answer("Отменено")
            return

        if action == AdminActions.MENU_MODE_ADD:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.set_state(AdminStates.menu_waiting_input)
            await state.update_data(
                menu_task="add_mode",
                menu_section_id=section.id,
            )
            await callback.message.edit_text(
                f"Введите название нового режима для раздела «{section.name}»:",
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_MODE_SELECT:
            if not callback_data.mode_id:
                await callback.answer("Режим не найден", show_alert=True)
                return
            result = await menu_repo.get_mode(callback_data.section_id, callback_data.mode_id)
            if not result:
                await callback.answer("Режим не найден", show_alert=True)
                return
            section, mode = result
            await state.update_data(
                menu_section_id=section.id,
                menu_mode_id=mode.id,
            )
            await state.set_state(AdminStates.menu_mode_detail)
            await callback.message.edit_text(
                f"{section.name} · {mode.name}. Выберите действие:",
                reply_markup=build_admin_menu_mode(section, mode.id),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_MODE_BACK:
            data = await state.get_data()
            section_id = data.get("menu_section_id") or callback_data.section_id
            section = await menu_repo.get_section(section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.set_state(AdminStates.menu_section_detail)
            await callback.message.edit_text(
                f"Раздел «{section.name}». Выберите действие:",
                reply_markup=build_admin_menu_section(section),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_MODE_RENAME:
            if not callback_data.mode_id:
                await callback.answer("Режим не найден", show_alert=True)
                return
            result = await menu_repo.get_mode(callback_data.section_id, callback_data.mode_id)
            if not result:
                await callback.answer("Режим не найден", show_alert=True)
                return
            section, mode = result
            await state.set_state(AdminStates.menu_waiting_input)
            await state.update_data(
                menu_task="rename_mode",
                menu_section_id=section.id,
                menu_mode_id=mode.id,
                previous_mode_name=mode.name,
            )
            await callback.message.edit_text(
                f"Введите новое название для режима «{mode.name}»:",
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_MODE_DELETE:
            if not callback_data.mode_id:
                await callback.answer("Режим не найден", show_alert=True)
                return
            result = await menu_repo.get_mode(callback_data.section_id, callback_data.mode_id)
            if not result:
                await callback.answer("Режим не найден", show_alert=True)
                return
            section, mode = result
            await state.set_state(AdminStates.menu_confirm)
            await state.update_data(
                menu_task="delete_mode",
                menu_section_id=section.id,
                menu_mode_id=mode.id,
                menu_mode_name=mode.name,
            )
            await callback.message.edit_text(
                f"Удалить режим «{mode.name}» в разделе «{section.name}»?",
                reply_markup=build_confirmation_keyboard(
                    AdminActions.MENU_MODE_DELETE_CONFIRM,
                    AdminActions.MENU_MODE_DELETE_CANCEL,
                    section.id,
                    mode.id,
                ),
            )
            await callback.answer()
            return

        if action == AdminActions.MENU_MODE_DELETE_CONFIRM:
            data = await state.get_data()
            if data.get("menu_task") != "delete_mode":
                await callback.answer("Операция уже отменена", show_alert=True)
                return
            try:
                section, deleted_mode = await menu_repo.delete_mode(
                    callback_data.section_id, callback_data.mode_id or ""
                )
            except KeyError:
                await callback.answer("Режим не найден", show_alert=True)
                return
            await storage.delete_mode(section.name, deleted_mode.name)
            await state.set_state(AdminStates.menu_section_detail)
            await state.update_data(menu_task=None, menu_mode_id=None)
            await callback.message.edit_text(
                f"Раздел «{section.name}». Выберите действие:",
                reply_markup=build_admin_menu_section(section),
            )
            await callback.answer("Режим удален")
            return

        if action == AdminActions.MENU_MODE_DELETE_CANCEL:
            section = await menu_repo.get_section(callback_data.section_id)
            if not section:
                await callback.answer("Раздел не найден", show_alert=True)
                return
            await state.set_state(AdminStates.menu_section_detail)
            await state.update_data(menu_task=None)
            await callback.message.edit_text(
                f"Раздел «{section.name}». Выберите действие:",
                reply_markup=build_admin_menu_section(section),
            )
            await callback.answer("Отменено")
            return

        await callback.answer("Неизвестное действие", show_alert=True)

    @router.message(AdminStates.waiting_video)
    async def on_video(message: Message, state: FSMContext) -> None:
        if not is_admin(message.from_user.id if message.from_user else None):
            return

        if not message.video:
            await message.answer("Пожалуйста, отправьте видеофайл.")
            return

        data = await state.get_data()
        section_id = data.get("video_section_id")
        mode_id = data.get("video_mode_id")
        if not section_id or not mode_id:
            await message.answer("Не удалось определить целевой режим. Начните заново.")
            await state.clear()
            return

        result = await menu_repo.get_mode(section_id, mode_id)
        if not result:
            await message.answer("Режим не найден. Попробуйте снова.")
            await state.clear()
            return
        section, mode = result

        await storage.set_video(section.name, mode.name, message.video.file_id)
        await message.answer("Видео обновлено.")

        await state.set_state(AdminStates.choosing_mode)
        await message.answer(
            f"{section.name}: выберите режим для изменения видео",
            reply_markup=build_admin_video_modes(section),
        )

    @router.message(AdminStates.menu_waiting_input)
    async def on_menu_input(message: Message, state: FSMContext) -> None:
        if not is_admin(message.from_user.id if message.from_user else None):
            return

        text = (message.text or "").strip()
        if not text:
            await message.answer("Название не может быть пустым. Попробуйте снова или используйте /cancel.")
            return

        data = await state.get_data()
        task = data.get("menu_task")

        if task == "add_section":
            sections = await menu_repo.get_sections()
            if any(section.name.lower() == text.lower() for section in sections):
                await message.answer("Раздел с таким названием уже существует.")
                return
            section = await menu_repo.add_section(text)
            await storage.add_section(section)
            await state.set_state(AdminStates.menu_section_detail)
            await state.update_data(menu_section_id=section.id, menu_task=None)
            await message.answer(
                f"Раздел «{section.name}» создан.",
                reply_markup=build_admin_menu_section(section),
            )
            return

        if task == "rename_section":
            section_id = data.get("menu_section_id")
            previous_name = data.get("previous_section_name")
            if not section_id or not previous_name:
                await message.answer("Не удалось определить раздел. Начните заново.")
                await state.clear()
                return
            sections = await menu_repo.get_sections()
            if any(section.name.lower() == text.lower() and section.id != section_id for section in sections):
                await message.answer("Другой раздел уже имеет такое название.")
                return
            updated_section = await menu_repo.rename_section(section_id, text)
            try:
                await storage.rename_section(previous_name, updated_section.name)
            except ValueError:
                await message.answer(
                    "Не удалось переименовать раздел в хранилище видео. Имя уже используется."
                )
                return
            await state.set_state(AdminStates.menu_section_detail)
            await state.update_data(menu_section_id=updated_section.id, menu_task=None)
            await message.answer(
                f"Раздел переименован в «{updated_section.name}».",
                reply_markup=build_admin_menu_section(updated_section),
            )
            return

        if task == "add_mode":
            section_id = data.get("menu_section_id")
            if not section_id:
                await message.answer("Не удалось определить раздел. Начните заново.")
                await state.clear()
                return
            section = await menu_repo.get_section(section_id)
            if not section:
                await message.answer("Раздел не найден. Начните заново.")
                await state.clear()
                return
            if any(mode.name.lower() == text.lower() for mode in section.modes):
                await message.answer("Режим с таким названием уже существует в этом разделе.")
                return
            updated_section, new_mode = await menu_repo.add_mode(section.id, text)
            await storage.add_mode(updated_section.name, new_mode.name)
            await state.set_state(AdminStates.menu_section_detail)
            await state.update_data(menu_section_id=updated_section.id, menu_task=None)
            await message.answer(
                f"Режим «{new_mode.name}» добавлен.",
                reply_markup=build_admin_menu_section(updated_section),
            )
            return

        if task == "rename_mode":
            section_id = data.get("menu_section_id")
            mode_id = data.get("menu_mode_id")
            previous_mode_name = data.get("previous_mode_name")
            if not section_id or not mode_id or not previous_mode_name:
                await message.answer("Не удалось определить режим. Начните заново.")
                await state.clear()
                return
            section = await menu_repo.get_section(section_id)
            if not section:
                await message.answer("Раздел не найден. Начните заново.")
                await state.clear()
                return
            if any(mode.name.lower() == text.lower() and mode.id != mode_id for mode in section.modes):
                await message.answer("Режим с таким названием уже существует.")
                return
            updated_section, updated_mode = await menu_repo.rename_mode(section_id, mode_id, text)
            try:
                await storage.rename_mode(
                    updated_section.name, previous_mode_name, updated_mode.name
                )
            except ValueError:
                await message.answer(
                    "Не удалось переименовать режим в хранилище видео. Имя уже используется."
                )
                return
            await state.set_state(AdminStates.menu_mode_detail)
            await state.update_data(
                menu_mode_id=updated_mode.id,
                menu_task=None,
            )
            await message.answer(
                f"Режим переименован в «{updated_mode.name}».",
                reply_markup=build_admin_menu_mode(updated_section, updated_mode.id),
            )
            return

        await message.answer("Неизвестная операция. Используйте /cancel и попробуйте снова.")

    return router

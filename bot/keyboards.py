from typing import Iterable

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import MenuSection


class UserMenuCallback(CallbackData, prefix="user-menu"):
    action: str
    section_id: str
    mode_id: str | None = None


class AdminMenuCallback(CallbackData, prefix="admin-menu"):
    action: str
    section_id: str
    mode_id: str | None = None


class AdminActions:
    VIDEO = "vid"
    VIDEO_CATEGORY = "vid_cat"
    VIDEO_MODE = "vid_mode"
    VIDEO_BACK = "vid_back"

    MENU = "menu"
    MENU_BACK = "menu_back"
    MENU_SECTION = "menu_sec"
    MENU_ADD_SECTION = "menu_add_sec"
    MENU_SECTION_RENAME = "menu_sec_ren"
    MENU_SECTION_DELETE = "menu_sec_del"
    MENU_SECTION_DELETE_CONFIRM = "menu_sec_del_yes"
    MENU_SECTION_DELETE_CANCEL = "menu_sec_del_no"
    MENU_SECTION_BACK = "menu_sec_back"

    MENU_MODE_SELECT = "menu_mode"
    MENU_MODE_ADD = "menu_mode_add"
    MENU_MODE_RENAME = "menu_mode_ren"
    MENU_MODE_DELETE = "menu_mode_del"
    MENU_MODE_DELETE_CONFIRM = "menu_mode_del_yes"
    MENU_MODE_DELETE_CANCEL = "menu_mode_del_no"
    MENU_MODE_BACK = "menu_mode_back"


def build_main_menu(menu: Iterable[MenuSection]):
    builder = InlineKeyboardBuilder()
    for section in menu:
        builder.button(
            text=section.name,
            callback_data=UserMenuCallback(action="category", section_id=section.id),
        )
    builder.adjust(2)
    return builder.as_markup()


def build_modes_menu(section: MenuSection):
    builder = InlineKeyboardBuilder()
    for mode in section.modes:
        builder.button(
            text=mode.name,
            callback_data=UserMenuCallback(
                action="mode", section_id=section.id, mode_id=mode.id
            ),
        )
    builder.button(
        text="🔙 Назад",
        callback_data=UserMenuCallback(action="back", section_id="", mode_id=None),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_admin_root_menu():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎞 Видео",
        callback_data=AdminMenuCallback(action=AdminActions.VIDEO, section_id="", mode_id=None),
    )
    builder.button(
        text="🗂 Меню",
        callback_data=AdminMenuCallback(action=AdminActions.MENU, section_id="", mode_id=None),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_admin_video_categories(menu: Iterable[MenuSection]):
    builder = InlineKeyboardBuilder()
    for section in menu:
        builder.button(
            text=section.name,
            callback_data=AdminMenuCallback(
                action=AdminActions.VIDEO_CATEGORY, section_id=section.id
            ),
        )
    builder.button(
        text="🔙 Назад",
        callback_data=AdminMenuCallback(action=AdminActions.VIDEO_BACK, section_id="", mode_id=None),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def build_admin_video_modes(section: MenuSection):
    builder = InlineKeyboardBuilder()
    for mode in section.modes:
        builder.button(
            text=mode.name,
            callback_data=AdminMenuCallback(
                action=AdminActions.VIDEO_MODE, section_id=section.id, mode_id=mode.id
            ),
        )
    builder.button(
        text="🔙 Назад",
        callback_data=AdminMenuCallback(action=AdminActions.VIDEO_BACK, section_id="", mode_id=None),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_admin_menu_sections(menu: Iterable[MenuSection]):
    builder = InlineKeyboardBuilder()
    for section in menu:
        builder.button(
            text=section.name,
            callback_data=AdminMenuCallback(
                action=AdminActions.MENU_SECTION, section_id=section.id
            ),
        )
    builder.button(
        text="➕ Добавить раздел",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_ADD_SECTION, section_id="", mode_id=None
        ),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=AdminMenuCallback(action=AdminActions.MENU_BACK, section_id="", mode_id=None),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_admin_menu_section(section: MenuSection):
    builder = InlineKeyboardBuilder()
    for mode in section.modes:
        builder.button(
            text=f"🎯 {mode.name}",
            callback_data=AdminMenuCallback(
                action=AdminActions.MENU_MODE_SELECT,
                section_id=section.id,
                mode_id=mode.id,
            ),
        )
    builder.button(
        text="➕ Добавить режим",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_MODE_ADD, section_id=section.id, mode_id=None
        ),
    )
    builder.button(
        text="✏️ Переименовать раздел",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_SECTION_RENAME, section_id=section.id, mode_id=None
        ),
    )
    builder.button(
        text="🗑 Удалить раздел",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_SECTION_DELETE, section_id=section.id, mode_id=None
        ),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_SECTION_BACK, section_id="", mode_id=None
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_admin_menu_mode(section: MenuSection, mode_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Переименовать",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_MODE_RENAME, section_id=section.id, mode_id=mode_id
        ),
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_MODE_DELETE, section_id=section.id, mode_id=mode_id
        ),
    )
    builder.button(
        text="🔙 Назад",
        callback_data=AdminMenuCallback(
            action=AdminActions.MENU_MODE_BACK, section_id=section.id, mode_id=None
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def build_confirmation_keyboard(confirm_action: str, cancel_action: str, section_id: str, mode_id: str | None = None):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да",
        callback_data=AdminMenuCallback(
            action=confirm_action, section_id=section_id, mode_id=mode_id
        ),
    )
    builder.button(
        text="❌ Нет",
        callback_data=AdminMenuCallback(
            action=cancel_action, section_id=section_id, mode_id=mode_id
        ),
    )
    builder.adjust(2)
    return builder.as_markup()

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from bot import (
    MenuRepository,
    VideoStorage,
    create_admin_router,
    create_user_router,
    load_config,
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)

    menu_repo = MenuRepository(config.menu_path)
    await menu_repo.load()

    initial_menu = await menu_repo.get_sections()
    storage = VideoStorage(config.videos_path)
    await storage.load(initial_menu)

    dp = Dispatcher()
    dp.include_router(create_user_router(menu_repo, storage))
    dp.include_router(create_admin_router(config.admin_ids, menu_repo, storage))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

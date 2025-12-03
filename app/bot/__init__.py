import os
import asyncio
from typing import Any, Dict, Callable, Awaitable

from aiogram import Bot, Dispatcher, types, BaseMiddleware

from bot.handlers import workflow
from db import SessionLocal
from model import model_service


async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Начало"),
        types.BotCommand(command="/city", description="Поменять город"),
        types.BotCommand(
            command="/top_k", description="Поменять количество релевантных результатов"
        ),
        types.BotCommand(command="/settings", description="Показать текущие настройки"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot):
    await set_commands(bot)


bot = Bot(token=os.environ.get("BOT_TOKEN"))
dp = Dispatcher()
dp.startup.register(on_startup)

dp.include_router(workflow.router)


class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = SessionLocal()
        data["session"] = session
        try:
            result = await handler(event, data)
        finally:
            session.close()
        return result


dp.update.middleware(DbMiddleware())


class ModelMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["model_service"] = model_service
        result = await handler(event, data)
        return result


dp.update.middleware(ModelMiddleware())


async def start_bot():
    try:
        print("Bot started")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, handle_signals=False)
    except asyncio.CancelledError:
        print("Bot polling task cancelled")
        await bot.session.close()
    except Exception as e:
        print(f"Bot polling task error: {e}")
        await bot.session.close()
    finally:
        print("Bot polling task finished")
        await bot.session.close()


async def stop_bot():
    await dp.storage.close()
    await bot.session.close()

import os
import asyncio

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import workflow


load_dotenv()
bot = Bot(token=os.environ.get("BOT_TOKEN"))
dp = Dispatcher()

dp.include_router(workflow.router)


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

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import workflow


async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=os.environ.get('BOT_TOKEN'))
    dp = Dispatcher()

    dp.include_router(workflow.router)
    print('Boss started')

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

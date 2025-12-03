from contextlib import asynccontextmanager
import logging
import asyncio
from dotenv import load_dotenv

from fastapi import FastAPI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    global bot_task  # Access the global variable
    logger.info("Starting application")
    from bot import start_bot, stop_bot

    bot_task = asyncio.create_task(start_bot())  # Start the bot in the background
    yield

    logger.info("Stopping application")
    await stop_bot()  # Stop the bot properly
    logger.info("Stopped bot")
    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            logger.info("Bot task cancelled")
        except Exception as e:
            logger.error(f"Error while cancelling bot task: {e}")


app = FastAPI(lifespan=lifespan)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}

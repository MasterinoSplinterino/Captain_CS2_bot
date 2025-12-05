import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot_config import TELEGRAM_BOT_TOKEN, RCON_HOST, RCON_PORT, RCON_PASSWORD
from handlers import router

async def main():
    logging.basicConfig(level=logging.INFO)
    
    logging.info(f"RCON Config: Host={RCON_HOST}, Port={RCON_PORT}, Password={'***' if RCON_PASSWORD else 'NOT SET'}")
    
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN is not set!")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(router)

    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped")

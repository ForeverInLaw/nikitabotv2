"""
Main application entry point for the Telegram bot.
Initializes all components, configures logging, sets up database and Redis connections,
registers handlers and middlewares, and starts the bot.
"""

import asyncio
import logging
import sys
from typing import Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.db.database import init_db, close_db
from app.handlers import common_handlers, user_handlers, admin_handlers
from app.middlewares.language_middleware import LanguageMiddleware
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main application function."""
    logger.info("Starting Telegram bot application...")
    
    bot = None
    dp = None
    
    try:
        # Initialize bot with default properties
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Initialize Redis storage for FSM
        try:
            storage = RedisStorage.from_url(settings.REDIS_URL)
            logger.info("Redis storage initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis storage: {e}")
            logger.info("Falling back to memory storage (FSM state will not persist)")
            from aiogram.fsm.storage.memory import MemoryStorage
            storage = MemoryStorage()
        
        # Initialize dispatcher
        dp = Dispatcher(storage=storage)
        
        # Initialize database
        try:
            await init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        
        # Register middlewares
        dp.message.middleware(LanguageMiddleware())
        dp.callback_query.middleware(LanguageMiddleware())
        logger.info("Middlewares registered")
        
        # Register routers
        logger.info("Registering routers in order: admin_handlers -> user_handlers -> common_handlers")
        dp.include_router(admin_handlers.router)
        logger.info("✓ admin_handlers.router registered")
        dp.include_router(user_handlers.router)
        logger.info("✓ user_handlers.router registered")
        dp.include_router(common_handlers.router)
        logger.info("✓ common_handlers.router registered")
        logger.info("Handler routers registered")
        
        # Log bot information
        bot_info = await bot.get_me()
        logger.info(f"Bot @{bot_info.username} (ID: {bot_info.id}) started successfully")
        
        # Start polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error during bot startup: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Shutting down bot...")
        
        if dp:
            await dp.storage.close()
            logger.info("Dispatcher storage closed")
        
        if bot:
            await bot.session.close()
            logger.info("Bot session closed")
        
        try:
            await close_db()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error, bot cannot start: {e}", exc_info=True)
        sys.exit(1)


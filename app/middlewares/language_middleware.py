"""
Language middleware for automatic user language detection and management.
Provides user data to handlers including language preference and user object.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class LanguageMiddleware(BaseMiddleware):
    """Middleware for handling user language preferences and user data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """Process event and inject user data."""
        
        user_id = event.from_user.id
        default_language = "en"
        
        # Extract language code from Telegram user if available
        telegram_lang = getattr(event.from_user, 'language_code', None)
        if telegram_lang and telegram_lang.lower() in ["en", "ru", "pl"]:
            default_language = telegram_lang.lower()
        
        try:
            user_service = UserService()
            
            # Get or create user
            user, is_new = await user_service.get_or_create_user(user_id, default_language)
            
            if user:
                # Check if user is blocked
                if user.is_blocked:
                    logger.warning(f"Blocked user {user_id} attempted to use bot")
                    from app.localization.locales import get_text
                    block_message = get_text("user_blocked_message", user.language_code)
                    
                    if isinstance(event, Message):
                        await event.answer(block_message)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(block_message, show_alert=True)
                    
                    return  # Stop processing for blocked users
                
                # Inject user data into handler context
                data["user_data"] = {
                    "user_id": user.telegram_id,
                    "language": user.language_code,
                    "is_new_user": is_new,
                    "user_db_obj": user
                }
                
                logger.debug(f"User {user_id} language: {user.language_code}, new: {is_new}")
            else:
                # Fallback if user creation failed
                logger.error(f"Failed to get or create user {user_id}")
                data["user_data"] = {
                    "user_id": user_id,
                    "language": default_language,
                    "is_new_user": True,
                    "user_db_obj": None
                }
            
        except Exception as e:
            logger.error(f"Error in LanguageMiddleware for user {user_id}: {e}", exc_info=True)
            # Provide fallback data to prevent handler crashes
            data["user_data"] = {
                "user_id": user_id,
                "language": default_language,
                "is_new_user": False,
                "user_db_obj": None
            }
        
        # Continue to handler
        return await handler(event, data)


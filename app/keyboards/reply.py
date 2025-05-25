"""
Reply keyboard generators for the Telegram bot.
Creates persistent keyboards that appear in the user's keyboard area.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.localization.locales import get_text


def create_main_menu_reply_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create main menu reply keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("start_order", language))],
            [
                KeyboardButton(text=get_text("view_cart", language)),
                KeyboardButton(text=get_text("my_orders", language))
            ],
            [
                KeyboardButton(text=get_text("help", language)),
                KeyboardButton(text=get_text("change_language", language)) # Added language change to reply keyboard
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False # Persistent menu
    )
    
    return keyboard




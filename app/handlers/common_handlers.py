"""
Common handlers for basic bot commands like /start, /help, /language.
These handlers are available to all users regardless of their state.
"""

import logging
from typing import Any, Dict, Union

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from app.keyboards.inline import create_language_keyboard, create_main_menu_keyboard, create_back_to_menu_keyboard
from app.keyboards.reply import create_main_menu_reply_keyboard # For /start
from app.services.user_service import UserService
from app.localization.locales import get_text

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    """
    Handle /start command. Shows language selection for new users or main menu for existing users.
    """
    try:
        # user_data is injected by LanguageMiddleware and contains language, user_id, is_new_user
        language = user_data.get("language", "en") 
        is_new_user_this_cycle = user_data.get("is_new_user", False) # Flag from middleware if user was just created
        user_id = user_data.get("user_id")
        
        # Check if the user *was* new before this /start command interaction (e.g. very first interaction)
        # The `is_new_user` flag from middleware indicates if user was created *during this event processing*.
        # For a more persistent "is this their first time ever" flag, we might need another DB field.
        # For now, if `is_new_user_this_cycle` is true, it means they were definitely new or DB access failed.
        
        user_service = UserService()
        db_user = user_data.get("user_db_obj") # Get user object from middleware
        
        # If db_user is None and is_new_user_this_cycle is True, it means get_or_create failed or they are truly new.
        # If db_user is present, then is_new_user_this_cycle indicates if it was *just* created.

        if not db_user and is_new_user_this_cycle: # Truly new or DB error prevented creation/fetch
            # Offer language selection
            welcome_text = get_text("choose_language_initial", "en") # Use a globally understood initial prompt
            keyboard = create_language_keyboard() # No current language passed, so no "back"
            await message.answer(welcome_text, reply_markup=keyboard)
        elif db_user: # User exists or was just created successfully
            welcome_text = get_text("welcome_back", language).format(
                username=message.from_user.first_name or message.from_user.username or get_text("default_username", language, default="User") # New locale
            )
            menu_keyboard_inline = create_main_menu_keyboard(language)
            # Also send reply keyboard for persistent menu
            menu_keyboard_reply = create_main_menu_reply_keyboard(language)
            await message.answer(welcome_text, reply_markup=menu_keyboard_reply) # First send reply keyboard
            await message.answer(get_text("main_menu", language), reply_markup=menu_keyboard_inline) # Then inline menu

        await state.clear()
        logger.info(f"User {user_id} started the bot. Language: {language}. DB User present: {db_user is not None}. New this cycle: {is_new_user_this_cycle}")
        
    except Exception as e:
        logger.error(f"Error in start command for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(get_text("error_occurred", user_data.get("language", "en")))


@router.callback_query(F.data.startswith("lang:"))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    try:
        user_service = UserService()
        user_id = callback.from_user.id
        
        selected_language = callback.data.split(":")[1]
        
        success = await user_service.set_user_language(user_id, selected_language)
        
        if not success:
             # Default to English for this specific error message if setting language failed
             await callback.answer(get_text("error_setting_language", "en"), show_alert=True)
             # Keep current user_data language or fallback if it's somehow lost
             current_language = user_data.get("language", "en")
        else:
            # Update middleware's user_data for the current event scope
            user_data["language"] = selected_language
            current_language = selected_language # Use the newly set language
            await callback.answer(get_text("language_saved", current_language))

        welcome_text = get_text("language_selected", current_language)
        main_menu_text = get_text("main_menu", current_language)
        
        menu_keyboard_inline = create_main_menu_keyboard(current_language)
        # Also send reply keyboard if it's the initial language selection
        # How to know if it's initial? If previous state was none or specific initial state.
        # For now, always send both on language change.
        menu_keyboard_reply = create_main_menu_reply_keyboard(current_language)
        
        # Edit the message that had the language buttons
        await callback.message.edit_text(
            welcome_text + "\n\n" + main_menu_text,
            reply_markup=menu_keyboard_inline
        )
        # Send the reply keyboard as a new message if it needs to be established/updated
        if callback.message.chat.type == "private": # Reply keyboards only in private chats
             await callback.message.answer(get_text("reply_keyboard_updated", current_language, default="Menu updated."), reply_markup=menu_keyboard_reply) # New locale

        logger.info(f"User {user_id} selected language: {current_language}")
        
    except Exception as e:
        logger.error(f"Error in language selection for user {callback.from_user.id}: {e}", exc_info=True)
        # Use language from user_data if available, else default for error message
        error_lang = user_data.get("language", "en")
        await callback.answer(get_text("error_occurred", error_lang), show_alert=True)


@router.callback_query(F.data == "cmd_language", StateFilter("*")) 
@router.message(Command("language"))
async def cmd_language(event: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any]):
    try:
        current_state = await state.get_state()
        if current_state is not None:
             await state.clear()
             # Notify state cleared if it was a message command. Callbacks usually edit message.
             if isinstance(event, types.Message): 
                 await event.answer(get_text("action_cancelled", user_data.get("language", "en")))

        current_language = user_data.get("language", "en")
        
        text = get_text("choose_language", current_language)
        # Pass current_language to add a "Back" button if user is already in a menu
        keyboard = create_language_keyboard(current_language=current_language) 
        
        if isinstance(event, types.Message):
            await event.answer(text, reply_markup=keyboard)
        elif isinstance(event, types.CallbackQuery):
             await event.message.edit_text(text, reply_markup=keyboard)
             await event.answer()
        
        logger.info(f"User {event.from_user.id} requested language change. Current lang: {current_language}")
        
    except Exception as e:
        logger.error(f"Error in language command for user {event.from_user.id}: {e}", exc_info=True)
        error_lang = user_data.get("language", "en")
        if isinstance(event, types.Message):
             await event.answer(get_text("error_occurred", error_lang))
        elif isinstance(event, types.CallbackQuery):
             await event.answer(get_text("error_occurred", error_lang), show_alert=True)


@router.message(Command("help"))
async def cmd_help(message: types.Message, user_data: Dict[str, Any]):
    try:
        language = user_data.get("language", "en")
        help_text = get_text("help_message", language)
        await message.answer(help_text, parse_mode="HTML", reply_markup=create_back_to_menu_keyboard(language))
        logger.info(f"User {message.from_user.id} requested help")
        
    except Exception as e:
        logger.error(f"Error in help command for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(get_text("error_occurred", user_data.get("language", "en")))


@router.callback_query(F.data == "main_menu", StateFilter("*")) 
async def show_main_menu_callback(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]): # Renamed to avoid conflict
    try:
        language = user_data.get("language", "en")
        await state.clear()

        text = get_text("main_menu", language)
        keyboard_inline = create_main_menu_keyboard(language)
        
        await callback.message.edit_text(text, reply_markup=keyboard_inline)
        
        # Ensure reply keyboard is also present
        if callback.message.chat.type == "private":
            reply_keyboard = create_main_menu_reply_keyboard(language)
            # Send a placeholder message with the reply keyboard if it might have been dismissed or changed
            await callback.message.answer(get_text("menu_activated", language, default="."), reply_markup=reply_keyboard)


        await callback.answer()
        logger.info(f"User {callback.from_user.id} navigated to main menu via callback.")
        
    except Exception as e:
        logger.error(f"Error showing main menu for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer(get_text("error_occurred", user_data.get("language", "en")), show_alert=True)


@router.callback_query(F.data == "show_help", StateFilter("*")) 
async def show_help_callback(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    try:
        language = user_data.get("language", "en")
        await state.clear()

        help_text = get_text("help_message", language)
        # Edit message and add back button
        await callback.message.edit_text(help_text, parse_mode="HTML", reply_markup=create_back_to_menu_keyboard(language))
        await callback.answer()
        logger.info(f"User {callback.from_user.id} viewed help via callback.")

    except Exception as e:
        logger.error(f"Error showing help for user {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer(get_text("error_occurred", user_data.get("language", "en")), show_alert=True)


@router.message(StateFilter(default_state, None)) # Handle messages when no FSM state is active
async def handle_unknown_message_default_state(message: types.Message, user_data: Dict[str, Any], state: FSMContext): # Added state
    """Handle unknown messages when user is not in any specific FSM state."""
    try:
        language = user_data.get("language", "en")
        is_new_user_this_cycle = user_data.get("is_new_user", False)
        db_user = user_data.get("user_db_obj")

        # If user is new and DB object wasn't created/fetched by middleware (e.g., first ever message before /start)
        if not db_user and is_new_user_this_cycle:
             # Redirect to /start which handles language selection for truly new users
             # Pass along the current user_data as it contains middleware's findings
             return await cmd_start(message, state, user_data)

        # For existing users or users whose state is clear, respond with unknown command and main menu
        text = get_text("unknown_command", language)
        keyboard_inline = create_main_menu_keyboard(language)
        
        await message.answer(text, reply_markup=keyboard_inline)
        
        # Ensure reply keyboard is also present
        if message.chat.type == "private":
            reply_keyboard = create_main_menu_reply_keyboard(language)
            await message.answer(get_text("menu_activated", language, default="."), reply_markup=reply_keyboard) # Placeholder for reply keyboard

        logger.info(f"User {message.from_user.id} sent unknown message '{message.text}' in default state.")

    except Exception as e:
        logger.error(f"Error handling unknown message for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer(get_text("error_occurred", user_data.get("language", "en")))

# Add new locales used:
# "default_username": {"en": "User", "ru": "Пользователь", "pl": "Użytkownik"},
# "reply_keyboard_updated": {"en": "Menu keyboard updated.", "ru": "Клавиатура меню обновлена.", "pl": "Klawiatura menu zaktualizowana."},
# "menu_activated": {"en": ".", "ru": ".", "pl": "."} (Silent message to ensure reply keyboard is shown)




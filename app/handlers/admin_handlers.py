"""
Admin handlers for order management, product administration, and system monitoring.
Only accessible to users with admin privileges.
Includes handlers for Product, Category, Manufacturer, Location and Stock management.
Order management includes: viewing orders, approving, rejecting, cancelling, changing status.
User management includes: listing, viewing details, blocking, unblocking.
Basic settings view and statistics display.
"""

import logging
from typing import Any, Dict, Optional, Union
from decimal import Decimal, InvalidOperation as DecimalInvalidOperation
from datetime import datetime 

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup 
from aiogram.utils.markdown import hbold, hitalic, hcode, hlink
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.user_service import UserService 
from app.localization.locales import get_text
from app.keyboards.inline import (
    create_admin_keyboard, 
    create_admin_order_actions_keyboard, 
    create_back_button, 
    create_admin_product_management_menu_keyboard,
    create_admin_category_management_menu_keyboard,
    create_admin_manufacturer_management_menu_keyboard,
    create_admin_location_management_menu_keyboard,
    create_admin_stock_management_menu_keyboard,
    create_confirmation_keyboard,
    create_admin_product_edit_options_keyboard,
    create_admin_localization_actions_keyboard,
    create_admin_select_lang_for_localization_keyboard,
    ITEMS_PER_PAGE_ADMIN, create_paginated_keyboard,
    create_admin_order_list_filters_keyboard, 
    create_admin_order_statuses_keyboard,
    create_admin_user_management_menu_keyboard, 
    create_admin_user_list_item_keyboard, 
)
from app.utils.helpers import (
    sanitize_input, validate_quantity, validate_stock_change_quantity, 
    format_price, format_datetime, OrderStatusEnum, get_order_status_emoji, get_payment_method_emoji
)
from config.settings import settings 

logger = logging.getLogger(__name__)
router = Router()

# --- Authorization Check ---
async def is_admin_user_check(user_id: int, user_service: UserService) -> bool:
    """Check if user is admin based on settings or DB."""
    if settings.ADMIN_CHAT_ID is not None and user_id == int(settings.ADMIN_CHAT_ID): # Ensure ADMIN_CHAT_ID is int if comparing
        return True
    return await user_service.is_admin(user_id)


# --- FSM States ---
class AdminProductStates(StatesGroup): 
    # (Existing states from previous_code - assumed unchanged for this task scope)
    VIEWING_PRODUCT_LIST = State()
    VIEWING_CATEGORY_LIST = State()
    VIEWING_MANUFACTURER_LIST = State()
    VIEWING_LOCATION_LIST = State()

    PRODUCT_AWAIT_MANUFACTURER_ID = State()
    PRODUCT_AWAIT_CATEGORY_ID = State()
    PRODUCT_AWAIT_COST = State()
    PRODUCT_AWAIT_SKU = State()
    PRODUCT_AWAIT_VARIATION = State()
    PRODUCT_AWAIT_IMAGE_URL = State()
    PRODUCT_AWAIT_LOCALIZATION_LANG_CODE = State()
    PRODUCT_AWAIT_LOCALIZATION_NAME = State()     
    PRODUCT_AWAIT_LOCALIZATION_DESCRIPTION = State()
    PRODUCT_CONFIRM_ADD = State()
    PRODUCT_AWAIT_EDIT_FIELD_VALUE = State()
    PRODUCT_SELECT_ENTITY_FOR_FIELD = State() 

    CATEGORY_AWAIT_NAME = State()
    CATEGORY_AWAIT_EDIT_NAME = State() 
    CATEGORY_SELECT_FOR_EDIT = State() 
    CATEGORY_SELECT_FOR_DELETE = State()

    MANUFACTURER_AWAIT_NAME = State()
    MANUFACTURER_AWAIT_EDIT_NAME = State() 
    MANUFACTURER_SELECT_FOR_EDIT = State()
    MANUFACTURER_SELECT_FOR_DELETE = State()

    LOCATION_AWAIT_NAME = State()
    LOCATION_AWAIT_ADDRESS = State()
    LOCATION_AWAIT_EDIT_NAME = State() 
    LOCATION_AWAIT_EDIT_ADDRESS = State()
    LOCATION_SELECT_FOR_EDIT = State()
    LOCATION_SELECT_FOR_DELETE = State()

    STOCK_SELECT_PRODUCT = State()
    STOCK_SELECT_LOCATION = State()
    STOCK_AWAIT_QUANTITY_CHANGE = State()
    # Note: The above states were already defined in the file from a previous task.
    # This is just confirming their presence as per the prompt.


class AdminOrderManagementStates(StatesGroup):
    CHOOSING_ORDER_ACTION = State() 
    VIEWING_ORDERS_LIST = State()   
    VIEWING_ORDER_DETAILS = State() 
    AWAITING_REJECTION_REASON = State()
    AWAITING_CANCELLATION_REASON = State() 
    SELECTING_NEW_STATUS = State()      
    AWAITING_STATUS_CHANGE_NOTES = State() 

class AdminUserManagementStates(StatesGroup):
    VIEWING_USER_LIST = State()
    VIEWING_USER_DETAILS = State()
    CONFIRM_BLOCK_USER = State()
    CONFIRM_UNBLOCK_USER = State()
    # SEARCHING_USER = State() # Future: For searching users

class AdminSettingsStates(StatesGroup):
    VIEWING_SETTINGS_MENU = State()
    # EDITING_SETTING = State() # Future: For editing specific settings

class AdminStatisticsStates(StatesGroup):
    VIEWING_STATS_MENU = State()
    # VIEWING_USER_STATS = State() # Future: For specific stats views


def format_admin_order_details(order_data: Dict[str, Any], lang: str) -> str:
    """Format order details for admin view. order_data comes from OrderService and is localized."""
    status_emoji = order_data.get("status_emoji", "") 
    payment_emoji = get_payment_method_emoji(order_data['payment_method_raw']) 

    details = f"{hbold(get_text('admin_order_details_title', lang).format(order_id=order_data['id']))}\n\n" \
              f"{get_text('user_id_label', lang, default='User ID')}: {hcode(str(order_data['user_id']))} ({order_data.get('user_display', '')})\n" \
              f"{get_text('status_label', lang, default='Status')}: {status_emoji} {hbold(order_data['status_display'])}\n" \
              f"{get_text('payment_label', lang, default='Payment')}: {payment_emoji} {order_data['payment_method_display']}\n" \
              f"{get_text('total_label', lang, default='Total')}: {hbold(order_data['total_amount_display'])}\n" \
              f"{get_text('created_at_label', lang, default='Created At')}: {order_data['created_at_display']}\n" \
              f"{get_text('updated_at_label', lang, default='Updated At')}: {format_datetime(datetime.fromisoformat(order_data['updated_at_iso']), lang=lang) if order_data.get('updated_at_iso') else get_text('not_available_short', lang, default='N/A')}\n"
    
    if order_data.get('admin_notes'):
        details += f"\n{hbold(get_text('admin_notes_label', lang))}:\n{hitalic(order_data['admin_notes'])}\n"

    details += f"\n{hbold(get_text('order_items_list', lang))}:\n"
    
    if order_data.get('items'):
        for item in order_data['items']: 
            details += get_text("order_item_admin_format", lang).format(
                name=item['product_name'], 
                location=item['location_name'], 
                quantity=item['quantity'],
                price=item['price_at_order_display'], 
                total=item['item_total_display'], 
                reserved_qty = item.get('reserved_quantity', 0) 
            ) + "\n"
    else:
        details += get_text("no_items_found", lang) + "\n"
        
    return details

# --- Main Admin Panel Entry ---
@router.message(Command("admin"))
async def admin_panel_command(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService() # Instantiate service
    if not await is_admin_user_check(message.from_user.id, user_service): 
        return await message.answer(get_text("admin_access_denied", lang))
    
    await state.clear() 
    await message.answer(get_text("admin_panel_title", lang), reply_markup=create_admin_keyboard(lang))

@router.callback_query(F.data == "admin_panel_main")
async def cq_admin_panel_main(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    await callback.message.edit_text(get_text("admin_panel_title", lang), reply_markup=create_admin_keyboard(lang))
    await callback.answer()

# --- User Management Handlers ---
@router.callback_query(F.data == "admin_users_menu")
async def cq_admin_users_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.set_state(AdminUserManagementStates.VIEWING_USER_LIST) # Initial state for this section
    # Show the menu with filter options
    keyboard = create_admin_user_management_menu_keyboard(lang)
    await callback.message.edit_text(get_text("admin_user_management_title", lang), reply_markup=keyboard)
    await callback.answer()

async def _send_paginated_user_list(
    event: Union[types.Message, types.CallbackQuery], 
    state: FSMContext, 
    user_data: Dict[str, Any], 
    is_blocked_filter: Optional[bool] = None, 
    page: int = 0
):
    lang = user_data.get("language", "en")
    user_service = UserService()
    
    # Admin check
    if not await is_admin_user_check(event.from_user.id, user_service):
        msg = get_text("admin_access_denied", lang)
        if isinstance(event, types.CallbackQuery): await event.answer(msg, show_alert=True)
        else: await event.answer(msg)
        return

    users_on_page_data, total_users = await user_service.list_users_for_admin(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN, 
        offset=page * ITEMS_PER_PAGE_ADMIN,
        is_blocked_filter=is_blocked_filter
    )
    
    filter_key = "admin_filter_all_users"
    if is_blocked_filter is True: filter_key = "admin_filter_blocked_users"
    elif is_blocked_filter is False: filter_key = "admin_filter_active_users"
    filter_display = get_text(filter_key, lang)

    title = get_text("admin_users_list_title", lang).format(filter=filter_display)

    if not users_on_page_data and page == 0:
        empty_text = title + "\n\n" + get_text("admin_no_users_found", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_admin_main_menu", lang, "admin_users_menu")).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
             await target_message.edit_text(empty_text, reply_markup=kb)
        else:
             await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery) and hasattr(event, 'answer'): await event.answer()
        return

    await state.set_state(AdminUserManagementStates.VIEWING_USER_LIST)
    # Store filter for back navigation from user details & for pagination itself
    await state.update_data(current_user_filter_type=filter_key, current_user_list_page=page) 

    filter_cb_part = "all"
    if is_blocked_filter is True: filter_cb_part = "blocked"
    elif is_blocked_filter is False: filter_cb_part = "active"
    
    base_cb_data_for_pagination = f"admin_users_list_page:{filter_cb_part}" # Page num will be appended by create_paginated_keyboard
    
    keyboard = create_paginated_keyboard(
        items=users_on_page_data, 
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=base_cb_data_for_pagination, # e.g. "admin_users_list_page:all"
        item_callback_prefix="admin_user_details", 
        language=lang,
        back_callback_key="back_to_admin_main_menu", 
        back_callback_data="admin_users_menu", # Back to the user filter menu
        total_items_override=total_users,
        item_text_key="name", # 'name' field from users_on_page_data as formatted by service
        item_id_key="telegram_id" # User's telegram_id as the unique identifier
    )
    
    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
        await target_message.edit_text(title, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target_message.answer(title, reply_markup=keyboard, parse_mode="HTML")
        
    if isinstance(event, types.CallbackQuery) and hasattr(event, 'answer'): await event.answer()

# Callback for selecting filter and for pagination on user list
@router.callback_query(StateFilter(AdminUserManagementStates.VIEWING_USER_LIST, AdminUserManagementStates.VIEWING_USER_DETAILS, None), F.data.startswith("admin_users_list_page:"))
async def cq_admin_users_list_navigate(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    parts = callback.data.split(":") # Expected: "admin_users_list_page", "filter_type", "page_num"
    filter_str = parts[1]
    page = int(parts[2])
    
    is_blocked_filter = None
    if filter_str == 'blocked': is_blocked_filter = True
    elif filter_str == 'active': is_blocked_filter = False

    await _send_paginated_user_list(callback, state, user_data, is_blocked_filter=is_blocked_filter, page=page)


@router.callback_query(StateFilter(AdminUserManagementStates.VIEWING_USER_LIST), F.data.startswith("admin_user_details:"))
async def cq_admin_view_user_details(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    telegram_id = int(callback.data.split(":")[1])
    
    user_details_data = await user_service.get_user_details_for_admin(telegram_id, lang)

    if not user_details_data:
        await callback.answer(get_text("admin_user_not_found", lang).format(id=telegram_id), show_alert=True)
        # Attempt to return to the user list (current page and filter)
        state_data = await state.get_data()
        filter_type_key = state_data.get("current_user_filter_type", "admin_filter_all_users")
        current_page = state_data.get("current_user_list_page", 0)
        
        is_blocked_filter = None
        if filter_type_key == "admin_filter_blocked_users": is_blocked_filter = True
        elif filter_type_key == "admin_filter_active_users": is_blocked_filter = False
        
        await _send_paginated_user_list(callback, state, user_data, is_blocked_filter=is_blocked_filter, page=current_page)
        return

    details_text = get_text("admin_user_details_title", lang).format(id=user_details_data['telegram_id']) + "\n\n"
    details_text += get_text("language_label", lang) + f": {user_details_data['language_code'].upper()}\n"
    details_text += get_text("status_label", lang) + f": {'🔒 ' + get_text('blocked_status', lang) if user_details_data['is_blocked'] else '🔓 ' + get_text('active_status', lang)}\n"
    details_text += get_text("is_admin_label", lang) + f": {'✅ ' + get_text('yes', lang) if user_details_data['is_admin_status'] else '❌ ' + get_text('no', lang)}\n"
    details_text += get_text("total_orders_label", lang) + f": {user_details_data['order_count']}\n"
    details_text += get_text("joined_date_label", lang) + f": {user_details_data['created_at_display']}\n"

    keyboard = create_admin_user_list_item_keyboard(user_details_data['telegram_id'], user_details_data['is_blocked'], lang)

    await state.set_state(AdminUserManagementStates.VIEWING_USER_DETAILS)
    await state.update_data(viewing_user_id=telegram_id) # Store for actions

    await callback.message.edit_text(details_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Back from user details to user list
@router.callback_query(StateFilter(AdminUserManagementStates.VIEWING_USER_DETAILS, AdminUserManagementStates.CONFIRM_BLOCK_USER, AdminUserManagementStates.CONFIRM_UNBLOCK_USER), F.data == "back_to_user_list")
async def cq_admin_back_to_user_list(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    filter_type_key = state_data.get("current_user_filter_type", "admin_filter_all_users") # default to "all" view
    current_page = state_data.get("current_user_list_page", 0)
    
    is_blocked_filter = None
    if filter_type_key == "admin_filter_blocked_users": is_blocked_filter = True
    elif filter_type_key == "admin_filter_active_users": is_blocked_filter = False
    
    await _send_paginated_user_list(callback, state, user_data, is_blocked_filter=is_blocked_filter, page=current_page)


@router.callback_query(StateFilter(AdminUserManagementStates.VIEWING_USER_DETAILS), F.data.startswith("admin_user_block_confirm_prompt:"))
async def cq_admin_block_user_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    telegram_id_to_block = int(callback.data.split(":")[1])
    
    await state.set_state(AdminUserManagementStates.CONFIRM_BLOCK_USER)
    # viewing_user_id is already set from user details view. Re-set to be sure.
    await state.update_data(user_to_block_id=telegram_id_to_block, viewing_user_id=telegram_id_to_block)


    confirm_text = get_text("admin_confirm_block_user", lang).format(id=telegram_id_to_block)
    keyboard = create_confirmation_keyboard(
        lang, 
        yes_callback=f"admin_user_block_execute:{telegram_id_to_block}", 
        no_callback=f"admin_user_details:{telegram_id_to_block}" 
    )
    await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(StateFilter(AdminUserManagementStates.CONFIRM_BLOCK_USER), F.data.startswith("admin_user_block_execute:"))
async def cq_admin_block_user_execute(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    telegram_id_to_block = int(callback.data.split(":")[1])
    
    success, message_key = await user_service.block_user_by_admin(telegram_id_to_block, callback.from_user.id)
    
    alert_text = get_text(message_key, lang).format(id=telegram_id_to_block) if success else get_text(message_key, lang)
    await callback.answer(alert_text, show_alert=True) # Show alert, especially on failure

    # After action, return to user details view, which will refresh its data
    # State is CONFIRM_BLOCK_USER, need to set back to VIEWING_USER_DETAILS to call details handler
    await state.set_state(AdminUserManagementStates.VIEWING_USER_DETAILS)
    # Create a mock callback with the correct data to reinvoke details view
    mock_callback_data = f"admin_user_details:{telegram_id_to_block}"
    # Re-use existing callback message if possible, or construct a new one for the call
    await cq_admin_view_user_details(
        types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_callback_data),
        user_data, 
        state
    )


@router.callback_query(StateFilter(AdminUserManagementStates.VIEWING_USER_DETAILS), F.data.startswith("admin_user_unblock_confirm_prompt:"))
async def cq_admin_unblock_user_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    telegram_id_to_unblock = int(callback.data.split(":")[1])
    
    await state.set_state(AdminUserManagementStates.CONFIRM_UNBLOCK_USER)
    await state.update_data(user_to_unblock_id=telegram_id_to_unblock, viewing_user_id=telegram_id_to_unblock)

    confirm_text = get_text("admin_confirm_unblock_user", lang).format(id=telegram_id_to_unblock)
    keyboard = create_confirmation_keyboard(
        lang, 
        yes_callback=f"admin_user_unblock_execute:{telegram_id_to_unblock}", 
        no_callback=f"admin_user_details:{telegram_id_to_unblock}"
    )
    await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(StateFilter(AdminUserManagementStates.CONFIRM_UNBLOCK_USER), F.data.startswith("admin_user_unblock_execute:"))
async def cq_admin_unblock_user_execute(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    telegram_id_to_unblock = int(callback.data.split(":")[1])

    success, message_key = await user_service.unblock_user_by_admin(telegram_id_to_unblock, callback.from_user.id)

    alert_text = get_text(message_key, lang).format(id=telegram_id_to_unblock) if success else get_text(message_key, lang)
    await callback.answer(alert_text, show_alert=True)
    
    await state.set_state(AdminUserManagementStates.VIEWING_USER_DETAILS)
    mock_callback_data = f"admin_user_details:{telegram_id_to_unblock}"
    await cq_admin_view_user_details(
        types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_callback_data),
        user_data, 
        state
    )


# --- Bot Parameter Settings Handlers ---
@router.callback_query(F.data == "admin_settings_menu")
async def cq_admin_settings_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.set_state(AdminSettingsStates.VIEWING_SETTINGS_MENU)
    
    settings_text = get_text("admin_settings_title", lang) + "\n\n"
    settings_text += hbold(get_text("admin_current_settings", lang)) + "\n"
    
    # Display current settings from config.settings (these are not editable via bot by default)
    settings_text += f"- {get_text('setting_bot_token', lang)}: {settings.BOT_TOKEN[:5]}***{settings.BOT_TOKEN[-3:] if len(settings.BOT_TOKEN) > 8 else ''}\n"
    settings_text += f"- {get_text('setting_admin_chat_id', lang)}: {settings.ADMIN_CHAT_ID or get_text('not_set', lang)}\n"
    settings_text += f"- {get_text('setting_order_timeout_hours', lang)}: {settings.ORDER_TIMEOUT_HOURS} {get_text('hours', lang, default='hours')}\n"
    # Add more settings from settings.py or a dynamic settings service if implemented

    # Keyboard only has back button for now. Future: add buttons to edit specific settings.
    keyboard = InlineKeyboardBuilder().row(create_back_button("back_to_admin_main_menu", lang, "admin_panel_main")).as_markup()

    await callback.message.edit_text(settings_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# --- Statistics View Handlers ---
@router.callback_query(F.data == "admin_stats_menu")
async def cq_admin_stats_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService() # For admin check and stats
    product_service = ProductService() # For product stats
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.set_state(AdminStatisticsStates.VIEWING_STATS_MENU)

    stats_data = await user_service.get_basic_statistics(lang) # UserService aggregates some stats

    stats_text = hbold(get_text("admin_statistics_title", lang)) + "\n\n"
    stats_text += get_text("stats_total_users", lang).format(count=stats_data.get("total_users", 0)) + "\n"
    stats_text += get_text("stats_active_users", lang).format(count=stats_data.get("active_users",0)) + "\n"
    stats_text += get_text("stats_blocked_users", lang).format(count=stats_data.get("blocked_users",0)) + "\n"
    stats_text += "-----\n"
    stats_text += get_text("stats_total_orders", lang).format(count=stats_data.get("total_orders",0)) + "\n"
    stats_text += get_text("stats_pending_orders", lang).format(count=stats_data.get("pending_orders",0)) + "\n"
    # stats_text += "-----\n"
    # Placeholder for product count until ProductService has a count method.
    # For now, we'll omit it or use a placeholder if ProductService cannot provide it easily.
    # total_products, _ = await product_service.list_all_entities_paginated("product", 0, 1, lang) # hack for total product count
    # stats_text += get_text("stats_total_products", lang).format(count=total_products if total_products is not None else get_text("not_available_short", lang)) + "\n"
    
    keyboard = InlineKeyboardBuilder().row(create_back_button("back_to_admin_main_menu", lang, "admin_panel_main")).as_markup()

    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# --- Order Management Handlers (largely existing, ensure they use updated is_admin_user_check) ---
@router.callback_query(F.data == "admin_orders_menu")
async def cq_admin_orders_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.set_state(AdminOrderManagementStates.CHOOSING_ORDER_ACTION)
    keyboard = create_admin_order_list_filters_keyboard(lang) 
    await callback.message.edit_text(get_text("admin_orders_title", lang), reply_markup=keyboard)
    await callback.answer()

async def _send_paginated_orders_list(
    event: Union[types.Message, types.CallbackQuery], 
    state: FSMContext, 
    user_data: Dict[str, Any], 
    status_filter: Optional[str] = None, 
    page: int = 0,
    filter_user_id: Optional[int] = None # Added for filtering orders by user ID
):
    lang = user_data.get("language", "en")
    order_service = OrderService()
    user_service = UserService() 

    if not await is_admin_user_check(event.from_user.id, user_service): 
         if isinstance(event, types.CallbackQuery): await event.answer(get_text("admin_access_denied", lang), show_alert=True)
         elif isinstance(event, types.Message): await event.answer(get_text("admin_access_denied", lang))
         return
    
    orders_on_page_data, total_orders = await order_service.get_orders_list_for_admin(
        language=lang, 
        limit=ITEMS_PER_PAGE_ADMIN, 
        offset=page * ITEMS_PER_PAGE_ADMIN,
        status_filter=status_filter,
        user_id_filter=filter_user_id
    )

    filter_display_name = get_text(f"order_status_{status_filter}", lang) if status_filter and status_filter in OrderStatusEnum.values() else get_text("admin_filter_all_orders_display", lang)
    title = get_text("admin_orders_list_title_status", lang).format(status=filter_display_name)
    if filter_user_id: title += f" (User ID: {filter_user_id})"


    if not orders_on_page_data and page == 0:
        empty_text = title + "\n\n" + (
            get_text("admin_no_orders_for_status", lang).format(status=filter_display_name) 
            if status_filter 
            else get_text("admin_no_orders_found", lang)
        )
        
        back_cb = "admin_users_menu" if filter_user_id else "admin_orders_menu"
        back_key = "back_to_user_list" if filter_user_id else "back_to_order_filters" # Or a more generic key
        kb = InlineKeyboardBuilder().row(create_back_button(back_key, lang, back_cb)).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
             await target_message.edit_text(empty_text, reply_markup=kb)
        else:
             await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery) and hasattr(event, 'answer'): await event.answer()
        return

    base_cb_data_for_pagination = f"admin_orders_list_page:{status_filter or 'all'}"
    if filter_user_id: base_cb_data_for_pagination += f":user{filter_user_id}"
        
    keyboard = create_paginated_keyboard(
        items=orders_on_page_data, 
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=base_cb_data_for_pagination,
        item_callback_prefix="admin_order_details", 
        language=lang,
        back_callback_key="back_to_order_filters" if not filter_user_id else "back_to_user_list", 
        back_callback_data="admin_orders_menu" if not filter_user_id else f"admin_user_details:{filter_user_id}",    
        total_items_override=total_orders,
        item_text_key="summary_text", # As formatted by OrderService.get_orders_list_for_admin
        item_id_key="id"
    )
    
    await state.set_state(AdminOrderManagementStates.VIEWING_ORDERS_LIST)
    # Store current filter and user_id for back navigation from order details
    await state.update_data(current_order_filter=status_filter, current_order_list_user_id=filter_user_id) 

    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
        await target_message.edit_text(title, reply_markup=keyboard, parse_mode="HTML") 
    else:
        await target_message.answer(title, reply_markup=keyboard, parse_mode="HTML") 
        
    if isinstance(event, types.CallbackQuery) and hasattr(event, 'answer'): await event.answer()


@router.callback_query(StateFilter(AdminOrderManagementStates.CHOOSING_ORDER_ACTION), F.data.startswith("admin_orders_filter:"))
async def cq_admin_filter_orders(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    status_filter = callback.data.split(":")[1]
    if status_filter == "all": status_filter = None
    
    await _send_paginated_orders_list(callback, state, user_data, status_filter=status_filter, page=0)

# Handler for viewing a specific user's orders (from user details panel)
@router.callback_query(F.data.startswith("admin_view_user_orders:"))
async def cq_admin_view_user_orders_list(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(":") # admin_view_user_orders:USER_ID:PAGE
    try:
        user_id_to_filter = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 0
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        return
    
    await _send_paginated_orders_list(callback, state, user_data, status_filter=None, page=page, filter_user_id=user_id_to_filter)


@router.callback_query(StateFilter(AdminOrderManagementStates.VIEWING_ORDERS_LIST), F.data.startswith("admin_orders_list_page:"))
async def cq_admin_orders_list_paginate(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    parts = callback.data.split(":") # admin_orders_list_page:STATUS_FILTER[:userUSER_ID]:PAGE_NUM
    status_filter_str = parts[1]
    user_id_filter = None
    page_num_str = parts[2]

    if "user" in page_num_str: # Format is admin_orders_list_page:STATUS:userUSERID:PAGE
        user_id_str_part = parts[2]
        user_id_filter = int(user_id_str_part.replace("user", ""))
        page_num_str = parts[3]
    
    page = int(page_num_str)
    status_filter = None if status_filter_str == "all" else status_filter_str
    
    await _send_paginated_orders_list(callback, state, user_data, status_filter=status_filter, page=page, filter_user_id=user_id_filter)


@router.callback_query(F.data.startswith("admin_order_details:")) # Allow from various states
async def cq_admin_view_order_details(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    order_id = int(callback.data.split(":")[1])
    
    order_service = OrderService()
    order_details_data = await order_service.get_order_details_for_admin(order_id, lang) 

    state_data = await state.get_data() 
    current_filter = state_data.get("current_order_filter", "all") 
    filter_user_id_for_back = state_data.get("current_order_list_user_id")


    if not order_details_data:
        await callback.answer(get_text("admin_order_not_found", lang).format(id=order_id), show_alert=True)
        back_cb_data = f"admin_orders_filter:{current_filter}"
        if filter_user_id_for_back:
             back_cb_data = f"admin_view_user_orders:{filter_user_id_for_back}:0" # Go to page 0 of user's orders
        
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_orders_list", lang, back_cb_data)).as_markup()
        try:
             await callback.message.edit_text(get_text("admin_order_not_found", lang).format(id=order_id), reply_markup=kb)
        except Exception:
             await callback.message.answer(get_text("admin_order_not_found", lang).format(id=order_id), reply_markup=kb)
        await callback.answer()
        return

    details_text = format_admin_order_details(order_details_data, lang)
    actions_keyboard = create_admin_order_actions_keyboard(order_id, order_details_data["status_raw"], lang)

    await state.set_state(AdminOrderManagementStates.VIEWING_ORDER_DETAILS)
    await state.update_data(
        current_order_id=order_id, 
        current_order_status_raw=order_details_data["status_raw"], 
        current_order_filter_for_back=current_filter, # Store filter for returning to correct list
        current_order_list_user_id_for_back=filter_user_id_for_back # Store user_id if list was filtered by user
    )
    
    await callback.message.edit_text(details_text, reply_markup=actions_keyboard, parse_mode="HTML")
    await callback.answer()

# ... (Rest of the order management handlers: approve, reject, cancel, change_status)
# These need to be updated to use the new state data for "back" navigation:
# current_order_filter_for_back and current_order_list_user_id_for_back

@router.callback_query(StateFilter(AdminOrderManagementStates.VIEWING_ORDER_DETAILS), F.data.startswith("admin_approve_order:"))
async def cq_admin_approve_order(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    order_id = int(callback.data.split(":")[1])
    order_service = OrderService()
    success, msg_key_or_error = await order_service.approve_order(order_id, callback.from_user.id, language=lang)
    
    alert_text = get_text(msg_key_or_error, lang) if success else msg_key_or_error 
    if success: alert_text = alert_text.format(id=order_id) 

    await callback.answer(alert_text, show_alert=True)

    state_data = await state.get_data()
    current_filter = state_data.get("current_order_filter_for_back", "all") 
    user_id_filter = state_data.get("current_order_list_user_id_for_back")
    await _send_paginated_orders_list(callback, state, user_data, status_filter=current_filter, page=0, filter_user_id=user_id_filter)


@router.callback_query(StateFilter(AdminOrderManagementStates.VIEWING_ORDER_DETAILS), F.data.startswith("admin_reject_order:"))
async def cq_admin_reject_order_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    order_id = int(callback.data.split(":")[1])
    
    await state.set_state(AdminOrderManagementStates.AWAITING_REJECTION_REASON)
    # current_order_filter_for_back and current_order_list_user_id_for_back are already in state
    await state.update_data(order_to_process_id=order_id) 

    prompt_text = get_text("admin_enter_rejection_reason", lang).format(order_id=order_id)
    cancel_text = get_text("cancel_prompt", lang)
    await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_text)}", parse_mode="HTML")
    await callback.answer()

@router.message(StateFilter(AdminOrderManagementStates.AWAITING_REJECTION_REASON), F.text)
async def fsm_admin_rejection_reason_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService() 
    if not await is_admin_user_check(message.from_user.id, user_service): return
    
    if message.text.lower() == "/cancel": # Handle /cancel command
        return await universal_cancel_admin_action(message, state, user_data)

    state_data = await state.get_data()
    order_id = state_data.get("order_to_process_id")
    current_filter = state_data.get("current_order_filter_for_back", "all")
    user_id_filter = state_data.get("current_order_list_user_id_for_back")
    reason = sanitize_input(message.text)

    if not order_id: 
        await message.answer(get_text("admin_action_failed_no_context", lang))
        return await admin_panel_command(message, state, user_data) 

    order_service = OrderService()
    success, msg_key = await order_service.reject_order(order_id, message.from_user.id, reason, language=lang)

    await message.answer(get_text(msg_key, lang).format(id=order_id))
    await _send_paginated_orders_list(message, state, user_data, status_filter=current_filter, page=0, filter_user_id=user_id_filter)


@router.callback_query(StateFilter(AdminOrderManagementStates.VIEWING_ORDER_DETAILS), F.data.startswith("admin_cancel_order:"))
async def cq_admin_cancel_order_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    order_id = int(callback.data.split(":")[1])
    await state.set_state(AdminOrderManagementStates.AWAITING_CANCELLATION_REASON)
    await state.update_data(order_to_process_id=order_id) 

    prompt_text = get_text("admin_enter_cancellation_reason", lang).format(order_id=order_id)
    cancel_text = get_text("cancel_prompt", lang)
    await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_text)}", parse_mode="HTML")
    await callback.answer()

@router.message(StateFilter(AdminOrderManagementStates.AWAITING_CANCELLATION_REASON), F.text)
async def fsm_admin_cancellation_reason_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service): return

    if message.text.lower() == "/cancel":
        return await universal_cancel_admin_action(message, state, user_data)

    state_data = await state.get_data()
    order_id = state_data.get("order_to_process_id")
    current_filter = state_data.get("current_order_filter_for_back", "all")
    user_id_filter = state_data.get("current_order_list_user_id_for_back")
    reason = sanitize_input(message.text)

    if not order_id: 
        await message.answer(get_text("admin_action_failed_no_context", lang))
        return await admin_panel_command(message, state, user_data)

    order_service = OrderService()
    success, msg_key = await order_service.cancel_order_by_admin(order_id, message.from_user.id, reason, language=lang) 
    
    await message.answer(get_text(msg_key, lang).format(id=order_id))
    await _send_paginated_orders_list(message, state, user_data, status_filter=current_filter, page=0, filter_user_id=user_id_filter)


@router.callback_query(StateFilter(AdminOrderManagementStates.VIEWING_ORDER_DETAILS), F.data.startswith("admin_change_order_status:"))
async def cq_admin_change_status_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    order_id = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    current_status_raw = state_data.get("current_order_status_raw") 

    if not current_status_raw: 
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        return 

    await state.set_state(AdminOrderManagementStates.SELECTING_NEW_STATUS)
    await state.update_data(order_to_process_id=order_id) 

    keyboard = create_admin_order_statuses_keyboard(lang, current_status_raw=current_status_raw, order_id=order_id)
    await callback.message.edit_text(get_text("admin_select_new_status_prompt", lang).format(order_id=order_id), reply_markup=keyboard)
    await callback.answer()

@router.callback_query(StateFilter(AdminOrderManagementStates.SELECTING_NEW_STATUS), F.data.startswith("admin_set_status:"))
async def cq_admin_set_new_status(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service): 
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
        
    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status_value = parts[2]
    state_data = await state.get_data()
    current_filter = state_data.get("current_order_filter_for_back", "all")
    user_id_filter = state_data.get("current_order_list_user_id_for_back")


    order_service = OrderService()
    success, msg_key_or_error = await order_service.change_order_status_by_admin(
        order_id, new_status_value, callback.from_user.id, 
        notes=None, 
        language=lang
    )

    alert_text = get_text(msg_key_or_error, lang) if success else msg_key_or_error
    if success: alert_text = alert_text.format(id=order_id, new_status=get_text(f"order_status_{new_status_value}", lang))

    await callback.answer(alert_text, show_alert=True)
    await _send_paginated_orders_list(callback, state, user_data, status_filter=current_filter, page=0, filter_user_id=user_id_filter)


# --- Universal Cancel for Admin FSM Actions ---
@router.message(Command("cancel"), StateFilter(AdminOrderManagementStates, AdminProductStates, AdminUserManagementStates, AdminSettingsStates, AdminStatisticsStates))
@router.callback_query(F.data == "cancel_admin_action", StateFilter(AdminOrderManagementStates, AdminProductStates, AdminUserManagementStates, AdminSettingsStates, AdminStatisticsStates))
async def universal_cancel_admin_action(event: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService() 
    if not await is_admin_user_check(event.from_user.id, user_service): 
        # This case should ideally be caught by middleware or earlier checks
        return await event.answer(get_text("admin_access_denied", lang)) if isinstance(event, types.Message) else await event.answer(get_text("admin_access_denied", lang), show_alert=True)

    current_fsm_state_obj = await state.get_state()
    logger.info(f"Admin {event.from_user.id} cancelling action from state {current_fsm_state_obj}")
    
    cancel_message_text = get_text("admin_action_cancelled", lang)
    response_target = event.message if isinstance(event, types.CallbackQuery) else event
    
    # Acknowledge cancellation
    if isinstance(event, types.CallbackQuery):
        await event.answer(cancel_message_text, show_alert=False)
    else:
        await response_target.answer(cancel_message_text)

    # Logic to determine where to go back
    state_data = await state.get_data() # Get FSM data before clearing

    # Default navigation target
    target_message_text = get_text("admin_panel_title", lang)
    target_reply_markup = create_admin_keyboard(lang)

    if current_fsm_state_obj:
        if current_fsm_state_obj.startswith("AdminOrderManagementStates:"):
            # If cancelling from order details or sub-flow, try to go back to relevant order list
            order_id_context = state_data.get("current_order_id") or state_data.get("order_to_process_id")
            if order_id_context and current_fsm_state_obj not in [AdminOrderManagementStates.CHOOSING_ORDER_ACTION, AdminOrderManagementStates.VIEWING_ORDERS_LIST]:
                # If we have an order_id, go back to its details view
                await state.set_state(AdminOrderManagementStates.VIEWING_ORDER_DETAILS) # Set for details handler
                # Re-invoke view order details
                mock_cb_data = f"admin_order_details:{order_id_context}"
                await cq_admin_view_order_details(
                    types.CallbackQuery(id=str(event.id), from_user=event.from_user, chat_instance=event.chat.id if hasattr(event, 'chat') else event.message.chat.id, message=response_target, data=mock_cb_data),
                    user_data, state
                )
                return 
            else: # Go to order filters menu
                target_message_text = get_text("admin_orders_title", lang)
                target_reply_markup = create_admin_order_list_filters_keyboard(lang)

        elif current_fsm_state_obj.startswith("AdminUserManagementStates:"):
            user_id_context = state_data.get("viewing_user_id") or state_data.get("user_to_block_id") or state_data.get("user_to_unblock_id")
            if user_id_context and current_fsm_state_obj not in [AdminUserManagementStates.VIEWING_USER_LIST]:
                 # Go back to user details view
                await state.set_state(AdminUserManagementStates.VIEWING_USER_DETAILS)
                mock_cb_data = f"admin_user_details:{user_id_context}"
                await cq_admin_view_user_details(
                     types.CallbackQuery(id=str(event.id), from_user=event.from_user, chat_instance=event.chat.id if hasattr(event, 'chat') else event.message.chat.id, message=response_target, data=mock_cb_data),
                     user_data, state
                )
                return
            else: # Go to user management main menu (filter selection)
                target_message_text = get_text("admin_user_management_title", lang)
                target_reply_markup = create_admin_user_management_menu_keyboard(lang)
        
        elif current_fsm_state_obj.startswith("AdminProductStates:"):
             target_message_text = get_text("admin_product_management_title", lang) 
             target_reply_markup = create_admin_product_management_menu_keyboard(lang) 
        
        elif current_fsm_state_obj.startswith("AdminSettingsStates:"):
             target_message_text = get_text("admin_settings_title", lang)
             target_reply_markup = InlineKeyboardBuilder().row(create_back_button("back_to_admin_main_menu", lang, "admin_panel_main")).as_markup() # Simple back for now
        
        elif current_fsm_state_obj.startswith("AdminStatisticsStates:"):
             target_message_text = get_text("admin_statistics_title", lang)
             target_reply_markup = InlineKeyboardBuilder().row(create_back_button("back_to_admin_main_menu", lang, "admin_panel_main")).as_markup() # Simple back for now

    await state.clear() # Clear state *after* deciding where to go

    # Edit message or send new one
    if hasattr(response_target, "edit_text") and isinstance(event, types.CallbackQuery):
        try:
            await response_target.edit_text(target_message_text, reply_markup=target_reply_markup, parse_mode="HTML")
        except Exception: 
            await response_target.answer(target_message_text, reply_markup=target_reply_markup, parse_mode="HTML")
    else: 
        await response_target.answer(target_message_text, reply_markup=target_reply_markup, parse_mode="HTML")


# Note: Product/Category/Manufacturer/Location/Stock management handlers are largely placeholders
# and would need full implementation similar to User and Order management.
# The focus of this update was User Management and setting up Settings/Stats views.


# --- Product Management Menu ---
@router.callback_query(F.data == "admin_products_menu")
async def cq_admin_products_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear() 
    await callback.message.edit_text(
        get_text("admin_product_management_title", lang),
        reply_markup=create_admin_product_management_menu_keyboard(lang)
    )
    await callback.answer()

# --- Category Management Menu ---
@router.callback_query(F.data == "admin_categories_menu")
async def cq_admin_categories_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    await callback.message.edit_text(
        get_text("admin_category_management_title", lang),
        reply_markup=create_admin_category_management_menu_keyboard(lang)
    )
    await callback.answer()

# --- Manufacturer Management Menu ---
@router.callback_query(F.data == "admin_manufacturers_menu")
async def cq_admin_manufacturers_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    await callback.message.edit_text(
        get_text("admin_manufacturer_management_title", lang),
        reply_markup=create_admin_manufacturer_management_menu_keyboard(lang)
    )
    await callback.answer()

# --- Location Management Menu ---
@router.callback_query(F.data == "admin_locations_menu")
async def cq_admin_locations_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    await callback.message.edit_text(
        get_text("admin_location_management_title", lang),
        reply_markup=create_admin_location_management_menu_keyboard(lang)
    )
    await callback.answer()

# --- Stock Management Menu ---
@router.callback_query(F.data == "admin_stock_menu")
async def cq_admin_stock_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    await callback.message.edit_text(
        get_text("admin_stock_management_title", lang),
        reply_markup=create_admin_stock_management_menu_keyboard(lang)
    )
    await callback.answer()


# --- Generic List Display Function (Internal Helper - if needed, or logic in each handler) ---
# Reusable logic for sending paginated lists can be refactored here if handlers become too repetitive.
# For now, keeping logic within each specific list handler as per detailed instructions.

# --- Product List Handlers ---
@router.callback_query(F.data.startswith("admin_prod_list"))
async def cq_admin_list_products(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = int(callback.data.split(':')[-1])
    product_service = ProductService()

    items, total_count = await product_service.list_all_products_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )

    title = get_text("admin_products_list_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_products_menu", lang, "admin_products_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_prod_list",
        item_callback_prefix="admin_view_prod",
        language=lang,
        back_callback_key="back_to_products_menu",
        back_callback_data="admin_products_menu",
        total_items_override=total_count,
        item_text_key="name", # Service already provides localized name
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.VIEWING_PRODUCT_LIST)
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_prod:"))
async def cq_admin_view_product_noop(callback: types.CallbackQuery, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    # item_id = callback.data.split(":")[1] # If needed for a more specific message
    await callback.answer(get_text("not_implemented_yet", lang), show_alert=True)


# --- Category List Handlers ---
@router.callback_query(F.data.startswith("admin_cat_list"))
async def cq_admin_list_categories(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = int(callback.data.split(':')[-1])
    product_service = ProductService()

    items, total_count = await product_service.list_all_categories_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )
    
    title = get_text("admin_categories_list_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_categories_menu", lang, "admin_categories_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_cat_list",
        item_callback_prefix="admin_view_cat",
        language=lang,
        back_callback_key="back_to_categories_menu",
        back_callback_data="admin_categories_menu",
        total_items_override=total_count,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.VIEWING_CATEGORY_LIST)
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_cat:"))
async def cq_admin_view_category_noop(callback: types.CallbackQuery, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    await callback.answer(get_text("not_implemented_yet", lang), show_alert=True)


# --- Stock Update Workflow Handlers ---

# Step 1: Select Product for Stock Update (Entry point from Stock Menu)
# The callback "admin_stock_select_prod:0" is set on the "Update Stock" button in create_admin_stock_management_menu_keyboard
@router.callback_query(F.data.startswith("admin_stock_select_prod:"))
async def cq_admin_stock_select_product(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = 0
    try:
        page = int(callback.data.split(':')[-1])
    except (IndexError, ValueError):
        logger.warning(f"Invalid page number in callback data: {callback.data}, defaulting to 0.")
        page = 0


    product_service = ProductService()

    items, total_count = await product_service.list_all_products_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )

    title = get_text("admin_stock_select_product_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_stock_menu", lang, "admin_stock_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_stock_select_prod", 
        item_callback_prefix="admin_stock_prod_sel", 
        language=lang,
        back_callback_key="back_to_stock_menu", 
        back_callback_data="admin_stock_menu",
        total_items_override=total_count,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.STOCK_SELECT_PRODUCT)
    # Store current page of product list for potential back navigation from location list
    await state.update_data(current_stock_update_product_list_page=page) 
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

# Step 2: Product Selected, Display Location List (or paginate location list)
# Callback from product selection: "admin_stock_prod_sel:PRODUCT_ID:PRODUCT_LIST_PAGE"
# Callback from location pagination: "admin_stock_loc_list_pg:PRODUCT_ID:PRODUCT_LIST_PAGE:LOCATION_LIST_PAGE"
@router.callback_query(
    StateFilter(AdminProductStates.STOCK_SELECT_PRODUCT, AdminProductStates.STOCK_SELECT_LOCATION), 
    F.data.startswith(("admin_stock_prod_sel:", "admin_stock_loc_list_pg:"))
)
async def cq_admin_stock_display_locations_for_product(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService() # For admin check
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id: int
    product_list_page_for_back: int
    location_list_page: int = 0 # Default for initial display

    if parts[0] == "admin_stock_prod_sel": # Coming from product selection
        product_id = int(parts[1])
        product_list_page_for_back = int(parts[2])
        # Store product_id and its list page, as we are now focusing on this product
        await state.update_data(
            stock_update_product_id=product_id,
            current_stock_update_product_list_page=product_list_page_for_back 
        )
    elif parts[0] == "admin_stock_loc_list_pg": # Coming from location list pagination
        product_id = int(parts[1])
        product_list_page_for_back = int(parts[2]) # Page of product list we came from
        location_list_page = int(parts[3]) # Page of location list to display
        # product_id should already be in state, this re-confirms/updates product_list_page for back button consistency
        await state.update_data(current_stock_update_product_list_page=product_list_page_for_back)
    else: # Should not happen
        await callback.answer("Invalid action.", show_alert=True)
        return

    fsm_data = await state.get_data()
    # Fetch product_name if not already in state, or use stored one
    product_name_for_title = fsm_data.get("stock_update_product_name")
    if not product_name_for_title or fsm_data.get("stock_update_product_id") != product_id: # If product_id changed or name not stored
        product_service_instance = ProductService()
        temp_product_details = await product_service_instance.get_product_details(product_id, location_id=0, language=lang) # loc_id dummy
        if not temp_product_details:
            await callback.answer(get_text("admin_stock_product_not_found", lang), show_alert=True)
            # Go back to product selection (using stored product list page)
            prev_prod_list_page = fsm_data.get("current_stock_update_product_list_page",0)
            mock_cb_data = f"admin_stock_select_prod:{prev_prod_list_page}"
            await cq_admin_stock_select_product(
                types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_cb_data), 
                user_data, state)
            return
        product_name_for_title = temp_product_details.get("name", f"ID {product_id}")
        await state.update_data(stock_update_product_name=product_name_for_title)


    product_service = ProductService()
    locations, total_locations = await product_service.get_locations_for_product_stock_admin(
        product_id=product_id, language=lang, limit=ITEMS_PER_PAGE_ADMIN, offset=location_list_page * ITEMS_PER_PAGE_ADMIN
    )
    
    title = get_text("admin_stock_select_location_title", lang).format(product_name=product_name_for_title)
    if not locations and location_list_page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang) 
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_product_selection_for_stock", lang, f"admin_stock_select_prod:{product_list_page_for_back}")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=locations,
        page=location_list_page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=f"admin_stock_loc_list_pg:{product_id}:{product_list_page_for_back}", 
        item_callback_prefix=f"admin_stock_loc_sel:{product_id}", 
        language=lang,
        back_callback_key="back_to_product_selection_for_stock", 
        back_callback_data=f"admin_stock_select_prod:{product_list_page_for_back}",
        total_items_override=total_locations,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.STOCK_SELECT_LOCATION)
    # Store current page of location list for potential back navigation from quantity prompt
    await state.update_data(current_stock_update_location_list_page=location_list_page)
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()


# Step 3: Location Selected, Prompt for Quantity
# Callback: "admin_stock_loc_sel:PRODUCT_ID:LOCATION_ID:LOCATION_LIST_PAGE"
@router.callback_query(StateFilter(AdminProductStates.STOCK_SELECT_LOCATION), F.data.startswith("admin_stock_loc_sel:"))
async def cq_admin_stock_location_selected(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id = int(parts[1])
    location_id = int(parts[2])
    location_list_page_this_item_was_on = int(parts[3]) if len(parts) > 3 else 0

    fsm_data = await state.get_data()
    # Ensure product_id from callback matches FSM, or prioritize callback's product_id
    if fsm_data.get("stock_update_product_id") != product_id:
        # This case should ideally not happen if flow is correct
        logger.warning("Product ID mismatch between callback and FSM state in stock location selection.")
        await state.update_data(stock_update_product_id=product_id) # Correct it

    product_name = fsm_data.get("stock_update_product_name", f"Product ID {product_id}")
    # This is the page of the *product list* we eventually want to go back to if user cancels all the way
    product_list_page_for_loc_list_back = fsm_data.get("current_stock_update_product_list_page", 0)

    product_service = ProductService()
    location_details = await product_service.get_location_by_id(location_id)
    if not location_details:
        await callback.answer(get_text("admin_stock_location_not_found", lang), show_alert=True)
        # Go back to location selection for this product, using the page this item was on
        mock_cb_data = f"admin_stock_loc_list_pg:{product_id}:{product_list_page_for_loc_list_back}:{location_list_page_this_item_was_on}"
        await cq_admin_stock_display_locations_for_product(
             types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_cb_data),
             user_data, state)
        return
    location_name = location_details.name

    current_stock_info = await product_service.get_stock_info(product_id, location_id)
    current_quantity = current_stock_info.get("quantity", 0) if current_stock_info else 0

    prompt_text = get_text("admin_stock_enter_quantity_prompt", lang).format(
        product_name=hbold(product_name), 
        location_name=hitalic(location_name),
        current_quantity=hcode(str(current_quantity))
    )
    prompt_text += f"\n\n{hitalic(get_text('cancel_prompt', lang))}"
    
    back_to_loc_list_cb = f"admin_stock_loc_list_pg:{product_id}:{product_list_page_for_loc_list_back}:{location_list_page_this_item_was_on}"
    kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_selection_for_stock", lang, back_to_loc_list_cb)).as_markup()

    await state.set_state(AdminProductStates.STOCK_AWAIT_QUANTITY_CHANGE)
    await state.update_data(
        stock_update_location_id=location_id,
        stock_update_location_name=location_name,
        stock_update_current_quantity_val=current_quantity
    )
    await callback.message.edit_text(prompt_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# Step 4: Quantity Received, Update Stock
@router.message(StateFilter(AdminProductStates.STOCK_AWAIT_QUANTITY_CHANGE), F.text)
async def fsm_admin_stock_quantity_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service_check = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service_check):
        await message.answer(get_text("admin_access_denied", lang))
        return

    if message.text.lower() == "/cancel":
        return await universal_cancel_admin_action(message, state, user_data)

    fsm_data = await state.get_data()
    product_id = fsm_data.get("stock_update_product_id")
    location_id = fsm_data.get("stock_update_location_id")
    product_name = fsm_data.get("stock_update_product_name", "N/A")
    location_name = fsm_data.get("stock_update_location_name", "N/A")
    current_q_val = fsm_data.get("stock_update_current_quantity_val", 0)

    if not all([product_id, location_id is not None]): # location_id can be 0, so check not None
        await message.answer(get_text("admin_action_failed_no_context", lang))
        await state.clear()
        # Re-invoke main admin panel as a safe exit
        # Construct a mock message or callback for admin_panel_command or cq_admin_panel_main
        # For simplicity, just send the text and keyboard
        await message.answer(get_text("admin_panel_title", lang), reply_markup=create_admin_keyboard(lang))
        return

    quantity_change_to_apply = validate_stock_change_quantity(message.text, current_q_val)

    if quantity_change_to_apply is None:
        # Re-prompt with error and original prompt details
        error_msg = get_text("invalid_quantity_format", lang)
        prompt_text = get_text("admin_stock_enter_quantity_prompt", lang).format(
            product_name=hbold(product_name), 
            location_name=hitalic(location_name),
            current_quantity=hcode(str(current_q_val))
        )
        prompt_text = f"{error_msg}\n\n{prompt_text}\n\n{hitalic(get_text('cancel_prompt', lang))}"
        
        product_list_page_for_loc_list_back = fsm_data.get("current_stock_update_product_list_page", 0)
        location_list_page_this_item_was_on = fsm_data.get("current_stock_update_location_list_page", 0) # Page of location list
        
        back_to_loc_list_cb = f"admin_stock_loc_list_pg:{product_id}:{product_list_page_for_loc_list_back}:{location_list_page_this_item_was_on}"
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_selection_for_stock", lang, back_to_loc_list_cb)).as_markup()
        await message.answer(prompt_text, reply_markup=kb, parse_mode="HTML")
        return

    product_service = ProductService()
    success, msg_key, new_final_quantity = await product_service.update_stock_by_admin(
        product_id=product_id,
        location_id=location_id,
        quantity_change=quantity_change_to_apply,
        admin_id=message.from_user.id,
        language=lang
    )

    final_message_text = ""
    if success:
        final_message_text = get_text(msg_key, lang).format(
            product_name=product_name, 
            location_name=location_name, 
            new_quantity=new_final_quantity
        )
    else:
        final_message_text = get_text(msg_key, lang).format(
            product_name=product_name, 
            location_name=location_name,
            current_quantity=current_q_val 
        )
    
    await message.answer(final_message_text)
    
    await state.clear()
    stock_menu_markup = create_admin_stock_management_menu_keyboard(lang)
    await message.answer(get_text("admin_stock_management_title", lang), reply_markup=stock_menu_markup)


# --- Stock Update Workflow Handlers ---

# Step 1: Select Product for Stock Update (Entry point from Stock Menu)
# The callback "admin_stock_select_prod:0" is set on the "Update Stock" button in create_admin_stock_management_menu_keyboard
@router.callback_query(F.data.startswith("admin_stock_select_prod:"))
async def cq_admin_stock_select_product(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = 0
    try:
        page = int(callback.data.split(':')[-1])
    except ValueError:
        logger.warning(f"Invalid page number in callback data: {callback.data}")
        # Default to page 0 or handle error appropriately

    product_service = ProductService()

    items, total_count = await product_service.list_all_products_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )

    title = get_text("admin_stock_select_product_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_stock_menu", lang, "admin_stock_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_stock_select_prod", 
        item_callback_prefix="admin_stock_prod_sel", # Shortened to avoid long callback data
        language=lang,
        back_callback_key="back_to_stock_menu", 
        back_callback_data="admin_stock_menu",
        total_items_override=total_count,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.STOCK_SELECT_PRODUCT)
    await state.update_data(current_stock_product_list_page=page) 
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

# Step 2: Product Selected, Select Location
# item_callback_prefix from previous step is "admin_stock_prod_sel"
# It will generate callbacks like "admin_stock_prod_sel:PRODUCT_ID:PRODUCT_LIST_PAGE"
@router.callback_query(StateFilter(AdminProductStates.STOCK_SELECT_PRODUCT), F.data.startswith("admin_stock_prod_sel:"))
async def cq_admin_stock_product_selected(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService() # For admin check
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id = int(parts[1])
    product_list_page_for_back = int(parts[2]) if len(parts) > 2 else 0
    
    location_list_page = 0
    # This specific handler is for initial location list. Pagination for locations will use a different callback.
    # If this callback includes more parts (e.g. admin_stock_prod_sel:PROD_ID:PROD_PAGE:LOC_PAGE for location pagination)
    # we need a different handler or more complex parsing.
    # For now, assume this is the first time locations are listed for this product.

    product_service = ProductService()
    
    # Fetch product name for the title. Use a lightweight method if available.
    # get_product_details is heavy; if only name is needed, a specific service method is better.
    # For now, we will use it as it's available.
    temp_product_details = await product_service.get_product_details(product_id, location_id=0, language=lang) # location_id=0 is a dummy value
    if not temp_product_details:
        await callback.answer(get_text("admin_stock_product_not_found", lang), show_alert=True)
        # Go back to product selection
        mock_cb_data = f"admin_stock_select_prod:{product_list_page_for_back}"
        # Need to call the handler directly as this is not a new callback, but a recovery
        await cq_admin_stock_select_product(
            types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_cb_data), 
            user_data, state
        )
        return
    product_name_for_title = temp_product_details.get("name", f"ID {product_id}")

    locations, total_locations = await product_service.get_locations_for_product_stock_admin(
        product_id=product_id, language=lang, limit=ITEMS_PER_PAGE_ADMIN, offset=location_list_page * ITEMS_PER_PAGE_ADMIN
    )
    
    title = get_text("admin_stock_select_location_title", lang).format(product_name=product_name_for_title)
    if not locations and location_list_page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang) # Could be "no locations found"
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_product_selection_for_stock", lang, f"admin_stock_select_prod:{product_list_page_for_back}")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    # For location list pagination, base_callback_data needs product_id and product_list_page_for_back
    # Item selection callback needs product_id and location_id
    keyboard = create_paginated_keyboard(
        items=locations,
        page=location_list_page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=f"admin_stock_loc_list_pg:{product_id}:{product_list_page_for_back}", # For location pagination
        item_callback_prefix=f"admin_stock_loc_sel:{product_id}", # For location selection
        language=lang,
        back_callback_key="back_to_product_selection_for_stock", # Text for back button
        back_callback_data=f"admin_stock_select_prod:{product_list_page_for_back}", # CB for back button
        total_items_override=total_locations,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.STOCK_SELECT_LOCATION)
    await state.update_data(
        stock_update_product_id=product_id, 
        stock_update_product_name=product_name_for_title, # Store for later use
        current_stock_product_list_page_for_back=product_list_page_for_back # Store for back nav from qty prompt
    )
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

# Handler for Location List Pagination (distinct from initial product selection)
@router.callback_query(StateFilter(AdminProductStates.STOCK_SELECT_LOCATION), F.data.startswith("admin_stock_loc_list_pg:"))
async def cq_admin_stock_location_list_paginate(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService() # For admin check
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id = int(parts[1])
    product_list_page_for_back = int(parts[2])
    location_list_page = int(parts[3]) # This is the new page for locations

    product_service = ProductService()
    fsm_data = await state.get_data()
    product_name_for_title = fsm_data.get("stock_update_product_name", f"ID {product_id}")


    locations, total_locations = await product_service.get_locations_for_product_stock_admin(
        product_id=product_id, language=lang, limit=ITEMS_PER_PAGE_ADMIN, offset=location_list_page * ITEMS_PER_PAGE_ADMIN
    )
    
    title = get_text("admin_stock_select_location_title", lang).format(product_name=product_name_for_title)
    # No need for empty check here as this is for pagination, initial empty check is in cq_admin_stock_product_selected

    keyboard = create_paginated_keyboard(
        items=locations,
        page=location_list_page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=f"admin_stock_loc_list_pg:{product_id}:{product_list_page_for_back}", 
        item_callback_prefix=f"admin_stock_loc_sel:{product_id}", 
        language=lang,
        back_callback_key="back_to_product_selection_for_stock", 
        back_callback_data=f"admin_stock_select_prod:{product_list_page_for_back}",
        total_items_override=total_locations,
        item_text_key="name",
        item_id_key="id"
    )
    # State is already STOCK_SELECT_LOCATION, just update message
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()


# Step 3: Location Selected, Prompt for Quantity
# item_callback_prefix from previous step is "admin_stock_loc_sel:PRODUCT_ID"
# It will generate callbacks like "admin_stock_loc_sel:PRODUCT_ID:LOCATION_ID:LOCATION_LIST_PAGE"
@router.callback_query(StateFilter(AdminProductStates.STOCK_SELECT_LOCATION), F.data.startswith("admin_stock_loc_sel:"))
async def cq_admin_stock_location_selected(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService() # For admin check
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id = int(parts[1])
    location_id = int(parts[2])
    location_list_page_for_back = int(parts[3]) if len(parts) > 3 else 0

    fsm_data = await state.get_data()
    product_name = fsm_data.get("stock_update_product_name", f"Product ID {product_id}")
    # product_list_page_for_back is already in FSM as current_stock_product_list_page_for_back
    # This is needed for the back button from quantity prompt to location list pagination
    orig_prod_page_for_loc_list_back = fsm_data.get("current_stock_product_list_page_for_back", 0)


    product_service = ProductService()
    location_details = await product_service.get_location_by_id(location_id)
    if not location_details:
        await callback.answer(get_text("admin_stock_location_not_found", lang), show_alert=True)
        # Go back to location selection for this product at its correct page
        mock_cb_data = f"admin_stock_loc_list_pg:{product_id}:{orig_prod_page_for_loc_list_back}:{location_list_page_for_back}"
        await cq_admin_stock_location_list_paginate(
            types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_cb_data),
            user_data, state
        )
        return
    location_name = location_details.name

    current_stock_info = await product_service.get_stock_info(product_id, location_id)
    current_quantity = current_stock_info.get("quantity", 0) if current_stock_info else 0

    prompt_text = get_text("admin_stock_enter_quantity_prompt", lang).format(
        product_name=hbold(product_name), 
        location_name=hitalic(location_name),
        current_quantity=hcode(str(current_quantity))
    )
    prompt_text += f"\n\n{hitalic(get_text('cancel_prompt', lang))}"
    
    # Back button for quantity prompt: goes to location list for the current product, at 'location_list_page_for_back'
    # It needs: product_id, product_list_page_for_back (for location list's own back button), and location_list_page_for_back
    back_to_loc_list_cb = f"admin_stock_loc_list_pg:{product_id}:{orig_prod_page_for_loc_list_back}:{location_list_page_for_back}"

    kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_selection_for_stock", lang, back_to_loc_list_cb)).as_markup()

    await state.set_state(AdminProductStates.STOCK_AWAIT_QUANTITY_CHANGE)
    await state.update_data(
        stock_update_location_id=location_id,
        stock_update_location_name=location_name, # Store for final message
        stock_update_current_quantity_val=current_quantity # Store for parsing input
        # product_id, product_name, current_stock_product_list_page_for_back are already in state
    )
    await callback.message.edit_text(prompt_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# Step 4: Quantity Received, Update Stock
@router.message(StateFilter(AdminProductStates.STOCK_AWAIT_QUANTITY_CHANGE), F.text)
async def fsm_admin_stock_quantity_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    # Admin check not strictly needed here if FSM entry is protected, but good practice
    user_service_check = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service_check):
        await message.answer(get_text("admin_access_denied", lang))
        return

    if message.text.lower() == "/cancel": # Universal cancel handler should pick this up if specific state is included
        # If specific cancel logic for this state is needed, handle here.
        # For now, assume universal_cancel_admin_action handles it or this is a fallback.
        return await universal_cancel_admin_action(message, state, user_data)


    fsm_data = await state.get_data()
    product_id = fsm_data.get("stock_update_product_id")
    location_id = fsm_data.get("stock_update_location_id")
    product_name = fsm_data.get("stock_update_product_name", "N/A") # Default if not found
    location_name = fsm_data.get("stock_update_location_name", "N/A") # Default if not found
    current_q = fsm_data.get("stock_update_current_quantity_val", 0)

    if not all([product_id, location_id]):
        await message.answer(get_text("admin_action_failed_no_context", lang))
        await state.clear()
        # Consider sending back to a safe menu, e.g., main admin menu
        await cq_admin_panel_main(types.CallbackQuery(id="dummy",from_user=message.from_user, chat_instance=message.chat.id, message=message, data="admin_panel_main"), state, user_data) # This is a bit hacky
        return

    # Use the helper to parse quantity
    quantity_change_to_apply = validate_stock_change_quantity(message.text, current_q)

    if quantity_change_to_apply is None:
        await message.answer(get_text("invalid_quantity_format", lang))
        # Re-prompt by re-sending the prompt message (state is still STOCK_AWAIT_QUANTITY_CHANGE)
        prompt_text = get_text("admin_stock_enter_quantity_prompt", lang).format(
            product_name=hbold(product_name), 
            location_name=hitalic(location_name),
            current_quantity=hcode(str(current_q))
        )
        prompt_text += f"\n\n{hitalic(get_text('cancel_prompt', lang))}"
        
        # Reconstruct back button for the prompt
        orig_prod_page_for_loc_list_back = fsm_data.get("current_stock_product_list_page_for_back", 0)
        # location_list_page_for_back was the page of the location list when a location was selected.
        # This might not be directly in fsm_data unless explicitly stored before going to quantity prompt.
        # Let's assume it was stored as 'current_stock_location_list_page_for_qty_back'
        loc_page_for_back_btn = fsm_data.get("current_stock_location_list_page", 0) # If we stored the location page

        back_to_loc_list_cb = f"admin_stock_loc_list_pg:{product_id}:{orig_prod_page_for_loc_list_back}:{loc_page_for_back_btn}"
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_selection_for_stock", lang, back_to_loc_list_cb)).as_markup()
        await message.answer(prompt_text, reply_markup=kb, parse_mode="HTML")
        return

    product_service = ProductService()
    success, msg_key, new_final_quantity = await product_service.update_stock_by_admin(
        product_id=product_id,
        location_id=location_id,
        quantity_change=quantity_change_to_apply, # This is the *change*, not the absolute value
        admin_id=message.from_user.id,
        language=lang
    )

    final_message_text = ""
    if success:
        final_message_text = get_text(msg_key, lang).format(
            product_name=product_name, 
            location_name=location_name, 
            new_quantity=new_final_quantity
        )
    else:
        final_message_text = get_text(msg_key, lang).format(
            product_name=product_name, 
            location_name=location_name,
            current_quantity=current_q # For error messages that need current_quantity
        )
    
    await message.answer(final_message_text)
    
    # Clear state and go back to stock menu for simplicity
    await state.clear()
    stock_menu_markup = create_admin_stock_management_menu_keyboard(lang)
    await message.answer(get_text("admin_stock_management_title", lang), reply_markup=stock_menu_markup)


# --- Stock Update Workflow Handlers ---

# Step 1: Select Product for Stock Update (Entry point from Stock Menu)
@router.callback_query(F.data.startswith("admin_stock_select_prod:"))
async def cq_admin_stock_select_product(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = int(callback.data.split(':')[-1])
    product_service = ProductService()

    items, total_count = await product_service.list_all_products_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )

    title = get_text("admin_stock_select_product_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_stock_menu", lang, "admin_stock_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_stock_select_prod", # For pagination of product list
        item_callback_prefix="admin_stock_prod_selected", # Prefix for item selection
        language=lang,
        back_callback_key="back_to_stock_menu", # Text for back button
        back_callback_data="admin_stock_menu",   # Callback for back button
        total_items_override=total_count,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.STOCK_SELECT_PRODUCT)
    await state.update_data(current_stock_product_list_page=page) # Store current product page for potential back navigation
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()


# Step 2: Product Selected, Select Location
@router.callback_query(StateFilter(AdminProductStates.STOCK_SELECT_PRODUCT), F.data.startswith("admin_stock_prod_selected:"))
async def cq_admin_stock_product_selected(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id = int(parts[1])
    # The page number in this callback (parts[2]) is the page of the *product list* this item was on.
    # We need it for the back button from the location list.
    product_list_page_for_back = int(parts[2]) if len(parts) > 2 else 0
    
    # Location list page, default to 0 if not specified (e.g. coming here for the first time for this product)
    location_list_page = 0 
    # If the callback is from location list pagination, it will have more parts
    # e.g. admin_stock_prod_selected:PRODUCT_ID:LOCATION_PAGE_NUM:ORIG_PROD_PAGE
    if len(parts) > 3 and parts[0] == "admin_stock_prod_selected_locpage": # custom prefix for this scenario
        product_id = int(parts[1]) # already have
        location_list_page = int(parts[2])
        product_list_page_for_back = int(parts[3])


    product_service = ProductService()
    
    # Fetch product name for the title
    # Using get_product_details, but only need name. A lighter service method might be better in future.
    product_details = await product_service.get_product_details(product_id, location_id=0, language=lang) # loc_id 0 is dummy
    if not product_details:
        await callback.answer(get_text("admin_stock_product_not_found", lang), show_alert=True)
        # Go back to product selection
        mock_cb_data = f"admin_stock_select_prod:{product_list_page_for_back}"
        await cq_admin_stock_select_product(types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_cb_data), user_data, state)
        return

    product_name = product_details.get("name", f"ID: {product_id}")

    locations, total_count = await product_service.get_locations_for_product_stock_admin(
        product_id=product_id,
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=location_list_page * ITEMS_PER_PAGE_ADMIN
    )
    
    title = get_text("admin_stock_select_location_title", lang).format(product_name=product_name)
    if not locations and location_list_page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang) # Could be a more specific "no locations"
        # Back button should go to product list page
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_product_selection_for_stock", lang, f"admin_stock_select_prod:{product_list_page_for_back}")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    # For location list pagination, we need product_id and original product_list_page for back button
    # The item_callback_prefix will carry product_id. The base_callback_data for pagination needs product_id and product_list_page
    base_cb_data_for_loc_pagination = f"admin_stock_prod_selected_locpage:{product_id}:{product_list_page_for_back}" # page num for loc list will be appended

    keyboard = create_paginated_keyboard(
        items=locations,
        page=location_list_page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=base_cb_data_for_loc_pagination, 
        item_callback_prefix=f"admin_stock_loc_selected:{product_id}", # Item click includes product_id
        language=lang,
        back_callback_key="back_to_product_selection_for_stock",
        back_callback_data=f"admin_stock_select_prod:{product_list_page_for_back}",
        total_items_override=total_count,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.STOCK_SELECT_LOCATION)
    await state.update_data(
        stock_update_product_id=product_id, 
        stock_update_product_name=product_name,
        current_stock_location_list_page=location_list_page,
        # product_list_page_for_back is implicitly handled by back_callback_data
    )
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()


# Step 3: Location Selected, Prompt for Quantity
@router.callback_query(StateFilter(AdminProductStates.STOCK_SELECT_LOCATION), F.data.startswith("admin_stock_loc_selected:"))
async def cq_admin_stock_location_selected(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(':')
    product_id = int(parts[1])
    location_id = int(parts[2])
    # The page number here (parts[3]) is the page of the *location list* this item was on.
    location_list_page_for_back = int(parts[3]) if len(parts) > 3 else 0


    fsm_data = await state.get_data()
    product_name = fsm_data.get("stock_update_product_name", f"ID: {product_id}")
    
    product_service = ProductService()
    location_details = await product_service.get_location_by_id(location_id)
    if not location_details:
        await callback.answer(get_text("admin_stock_location_not_found", lang), show_alert=True)
        # Go back to location selection for that product
        # Need original product_list_page from fsm_data if we stored it, or from previous state's back button.
        # For simplicity, we'll assume product_list_page_for_back was correctly set for the location list's back button
        # This is complex, for now just go back to location list page 0 for this product.
        # A more robust solution would pass product_list_page_for_back through state or callback data.
        # The cq_admin_stock_product_selected handler's back_callback_data for location list pagination already points to the correct product list page.
        # We need to use current_stock_location_list_page from FSM for this.
        
        # This callback needs to know the original product list page to construct the back button for location list
        # Let's assume current_stock_product_list_page is in FSM from cq_admin_stock_select_product
        orig_prod_page = fsm_data.get("current_stock_product_list_page", 0)

        mock_cb_data = f"admin_stock_prod_selected:{product_id}:{orig_prod_page}" # This takes it to location list for product_id, from prod list page orig_prod_page
        await cq_admin_stock_product_selected(types.CallbackQuery(id=callback.id, from_user=callback.from_user, chat_instance=callback.chat_instance, message=callback.message, data=mock_cb_data), user_data, state)

        return

    location_name = location_details.name

    current_stock_info = await product_service.get_stock_info(product_id, location_id)
    current_quantity = current_stock_info.get("quantity", 0) if current_stock_info else 0

    prompt_text = get_text("admin_stock_enter_quantity_prompt", lang).format(
        product_name=hbold(product_name), 
        location_name=hitalic(location_name),
        current_quantity=hcode(str(current_quantity))
    )
    prompt_text += f"\n\n{hitalic(get_text('cancel_prompt', lang))}"

    # Back button should go to location list for the current product, at the correct page
    # It needs: product_id, location_list_page_for_back, and the original product_list_page for *that* back button
    orig_prod_page_for_loc_list_back = fsm_data.get("current_stock_product_list_page", 0)
    
    # The callback for selecting a location from the paginated list of locations.
    # This needs to go to the location list for the product `product_id`, 
    # using `location_list_page_for_back` as the page for that list.
    # The back button from *that* location list then needs `orig_prod_page_for_loc_list_back`.
    # So, the callback would be something like: admin_stock_prod_selected_locpage:PRODUCT_ID:LOCATION_PAGE:ORIG_PROD_PAGE
    back_to_loc_list_cb = f"admin_stock_prod_selected_locpage:{product_id}:{location_list_page_for_back}:{orig_prod_page_for_loc_list_back}"

    kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_selection_for_stock", lang, back_to_loc_list_cb)).as_markup()

    await state.set_state(AdminProductStates.STOCK_AWAIT_QUANTITY_CHANGE)
    await state.update_data(
        stock_update_location_id=location_id,
        stock_update_location_name=location_name,
        stock_update_current_quantity_val=current_quantity,
        # product_id and product_name already in state
        # location_list_page_for_back is stored for the back button from quantity prompt
        current_stock_qty_prompt_loc_page = location_list_page_for_back 
    )
    await callback.message.edit_text(prompt_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# Step 4: Quantity Received, Update Stock
@router.message(StateFilter(AdminProductStates.STOCK_AWAIT_QUANTITY_CHANGE), F.text)
async def fsm_admin_stock_quantity_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        # This check is more for direct state access, admin status assumed by FSM entry
        await message.answer(get_text("admin_access_denied", lang))
        return

    if message.text.lower() == "/cancel":
        return await universal_cancel_admin_action(message, state, user_data)

    fsm_data = await state.get_data()
    product_id = fsm_data.get("stock_update_product_id")
    location_id = fsm_data.get("stock_update_location_id")
    product_name = fsm_data.get("stock_update_product_name", "N/A")
    location_name = fsm_data.get("stock_update_location_name", "N/A")
    current_quantity_val = fsm_data.get("stock_update_current_quantity_val", 0)

    if not all([product_id, location_id]):
        await message.answer(get_text("admin_action_failed_no_context", lang))
        await state.clear()
        # Go back to main admin panel or stock menu
        await admin_panel_command(message, state, user_data) # Assuming this is a valid way to restart
        return

    parsed_quantity_change = validate_stock_change_quantity(message.text, current_quantity_val)

    if parsed_quantity_change is None:
        await message.answer(get_text("invalid_quantity_format", lang))
        # Re-prompt (the state is still STOCK_AWAIT_QUANTITY_CHANGE)
        # Optionally, resend the prompt message if it got cleared or for clarity
        prompt_text = get_text("admin_stock_enter_quantity_prompt", lang).format(
            product_name=hbold(product_name), 
            location_name=hitalic(location_name),
            current_quantity=hcode(str(current_quantity_val))
        )
        prompt_text += f"\n\n{hitalic(get_text('cancel_prompt', lang))}"
        
        orig_prod_page_for_loc_list_back = fsm_data.get("current_stock_product_list_page", 0)
        location_list_page_for_back = fsm_data.get("current_stock_qty_prompt_loc_page",0)
        back_to_loc_list_cb = f"admin_stock_prod_selected_locpage:{product_id}:{location_list_page_for_back}:{orig_prod_page_for_loc_list_back}"
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_selection_for_stock", lang, back_to_loc_list_cb)).as_markup()

        await message.answer(prompt_text, reply_markup=kb, parse_mode="HTML")
        return

    product_service = ProductService()
    success, msg_key, new_quantity = await product_service.update_stock_by_admin(
        product_id=product_id,
        location_id=location_id,
        quantity_change=parsed_quantity_change,
        admin_id=message.from_user.id,
        language=lang
    )

    response_text = ""
    if success:
        response_text = get_text(msg_key, lang).format(
            product_name=product_name, 
            location_name=location_name, 
            new_quantity=new_quantity
        )
    else:
        response_text = get_text(msg_key, lang).format(
            product_name=product_name, 
            location_name=location_name,
            current_quantity=current_quantity_val # For error messages that need it
        )
    
    await message.answer(response_text)
    
    # Clear state and go back to stock menu (or product selection for stock)
    await state.clear()
    # For simplicity, go back to the main stock menu
    stock_menu_markup = create_admin_stock_management_menu_keyboard(lang)
    await message.answer(get_text("admin_stock_management_title", lang), reply_markup=stock_menu_markup)


# --- Manufacturer List Handlers ---
@router.callback_query(F.data.startswith("admin_mfg_list"))
async def cq_admin_list_manufacturers(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = int(callback.data.split(':')[-1])
    product_service = ProductService()

    items, total_count = await product_service.list_all_manufacturers_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )

    title = get_text("admin_manufacturers_list_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_manufacturers_menu", lang, "admin_manufacturers_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_mfg_list",
        item_callback_prefix="admin_view_mfg",
        language=lang,
        back_callback_key="back_to_manufacturers_menu",
        back_callback_data="admin_manufacturers_menu",
        total_items_override=total_count,
        item_text_key="name",
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.VIEWING_MANUFACTURER_LIST)
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_mfg:"))
async def cq_admin_view_manufacturer_noop(callback: types.CallbackQuery, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    await callback.answer(get_text("not_implemented_yet", lang), show_alert=True)


# --- Location List Handlers ---
@router.callback_query(F.data.startswith("admin_loc_list"))
async def cq_admin_list_locations(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    page = int(callback.data.split(':')[-1])
    product_service = ProductService()

    items, total_count = await product_service.list_all_locations_paginated(
        language=lang,
        limit=ITEMS_PER_PAGE_ADMIN,
        offset=page * ITEMS_PER_PAGE_ADMIN
    )

    title = get_text("admin_locations_list_title", lang)
    if not items and page == 0:
        empty_text = title + "\n\n" + get_text("no_items_found_admin", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_locations_menu", lang, "admin_locations_menu")).as_markup()
        await callback.message.edit_text(empty_text, reply_markup=kb)
        await callback.answer()
        return

    keyboard = create_paginated_keyboard(
        items=items,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_loc_list",
        item_callback_prefix="admin_view_loc",
        language=lang,
        back_callback_key="back_to_locations_menu",
        back_callback_data="admin_locations_menu",
        total_items_override=total_count,
        item_text_key="name", # As per instruction, can be enhanced later
        item_id_key="id"
    )
    await state.set_state(AdminProductStates.VIEWING_LOCATION_LIST)
    await callback.message.edit_text(title, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_loc:"))
async def cq_admin_view_location_noop(callback: types.CallbackQuery, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    await callback.answer(get_text("not_implemented_yet", lang), show_alert=True)
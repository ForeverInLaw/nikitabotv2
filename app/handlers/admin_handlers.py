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
from app.services.location_service import LocationService # Import LocationService
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
    MANUFACTURER_CONFIRM_DELETE = State() # New state

    LOCATION_AWAIT_NAME = State()
    LOCATION_AWAIT_ADDRESS = State()
    LOCATION_AWAIT_EDIT_NAME = State() 
    LOCATION_AWAIT_EDIT_ADDRESS = State()
    LOCATION_SELECT_FOR_EDIT = State()
    LOCATION_SELECT_FOR_DELETE = State()
    LOCATION_CONFIRM_DELETE = State() # New state for location deletion confirmation

    STOCK_SELECT_PRODUCT = State() 
    STOCK_SELECT_LOCATION = State() 
    STOCK_AWAIT_QUANTITY_CHANGE = State() 


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


@router.callback_query(F.data.startswith("admin_edit_location_start:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))
async def cq_admin_edit_location_start(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    location_id = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    
    # Ensure current_location_id and name are in state, fetch if not (e.g. direct entry to edit)
    current_location_name_from_state = state_data.get("current_location_name")
    if state_data.get("current_location_id") != location_id or not current_location_name_from_state:
        location_details = await location_service.get_location_details(location_id, lang)
        if not location_details:
            await callback.answer(get_text("admin_location_not_found_error", lang), show_alert=True)
            current_page = state_data.get("current_location_list_page", 0) # Attempt to go back to list
            return await _send_paginated_locations_list(callback, state, user_data, page=current_page)
        # Update state with fetched details
        await state.update_data(
            current_location_id=location_id, 
            current_location_name=location_details['name'],
            current_location_address=location_details.get('address', get_text("not_specified_placeholder", lang))
        )
        location_name_for_prompt = location_details['name']
    else:
        location_name_for_prompt = current_location_name_from_state

    # Assuming create_admin_location_edit_options_keyboard will be defined in app.keyboards.inline
    from app.keyboards.inline import create_admin_location_edit_options_keyboard 
    keyboard = create_admin_location_edit_options_keyboard(location_id, lang)
    
    await callback.message.edit_text(
        get_text("admin_what_to_edit_location", lang, name=location_name_for_prompt), 
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_edit_location_field:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))
async def cq_admin_edit_location_field_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(":") # Expected: admin_edit_location_field:FIELD_NAME
    field_to_edit = parts[1] 
    await state.update_data(editing_location_field=field_to_edit)

    prompt_text_key = ""
    if field_to_edit == "name":
        await state.set_state(AdminProductStates.LOCATION_AWAIT_EDIT_NAME)
        prompt_text_key = "admin_enter_new_location_name_prompt"
    elif field_to_edit == "address":
        await state.set_state(AdminProductStates.LOCATION_AWAIT_EDIT_ADDRESS)
        prompt_text_key = "admin_enter_new_location_address_prompt"
    else: # Should not happen with a fixed keyboard
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        return

    prompt_text = get_text(prompt_text_key, lang)
    cancel_info = get_text("cancel_prompt", lang)
    await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")
    await callback.answer()

@router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_EDIT_NAME, AdminProductStates.LOCATION_AWAIT_EDIT_ADDRESS), F.text)
async def fsm_admin_location_edit_value_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    state_data = await state.get_data()
    location_id = state_data.get("current_location_id")

    if message.text.lower() == "/cancel":
        if location_id: 
            await state.set_state(AdminProductStates.LOCATION_SELECT_FOR_EDIT)
            temp_message_for_edit = await message.answer(get_text("loading_text", lang, default="."), reply_markup=types.ReplyKeyboardRemove())
            mock_callback = types.CallbackQuery(
                id=str(message.message_id) + "_cancel_loc_edit", 
                from_user=message.from_user,
                chat_instance=str(message.chat.id), 
                message=temp_message_for_edit, 
                data=f"admin_location_actions:{location_id}"
            )
            return await cq_admin_location_actions(mock_callback, user_data, state)
        else: 
            return await universal_cancel_admin_action(message, state, user_data)

    new_value = sanitize_input(message.text)
    current_fsm_state = await state.get_state()

    if not new_value and current_fsm_state == AdminProductStates.LOCATION_AWAIT_EDIT_NAME:
        await message.answer(get_text("admin_location_name_empty_error", lang))
        prompt_text = get_text("admin_enter_new_location_name_prompt", lang) # Re-prompt for name
        cancel_info = get_text("cancel_prompt", lang)
        await message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")
        return
    
    if new_value == "-" and current_fsm_state == AdminProductStates.LOCATION_AWAIT_EDIT_ADDRESS: 
        new_value = None 

    field_to_edit = state_data.get("editing_location_field")
    
    if not location_id or not field_to_edit: 
        await message.answer(get_text("admin_action_failed_no_context", lang))
        await state.clear()
        from app.keyboards.inline import create_admin_location_management_menu_keyboard # For fallback
        keyboard = create_admin_location_management_menu_keyboard(lang)
        await message.answer(get_text("admin_location_management_title", lang), reply_markup=keyboard)
        return

    name_arg, address_arg = None, None
    if field_to_edit == "name":
        name_arg = new_value
    elif field_to_edit == "address":
        address_arg = new_value
    
    updated_location_dict, error_message_key = await location_service.update_location_details(
        location_id, name=name_arg, address=address_arg, lang=lang
    )

    original_name_before_edit = state_data.get("current_location_name", "") # For error messages

    if updated_location_dict:
        await message.answer(get_text("admin_location_updated_successfully", lang, name=updated_location_dict['name']))
        # Update state with potentially new name/address for the actions menu
        await state.update_data(
            current_location_name=updated_location_dict['name'],
            current_location_address=updated_location_dict.get('address', get_text("not_specified_placeholder", lang))
        )
    else:
        await message.answer(get_text(error_message_key or "admin_location_update_failed_error", lang, name=original_name_before_edit))

    # Always return to location actions menu for the current location_id
    await state.set_state(AdminProductStates.LOCATION_SELECT_FOR_EDIT) 
    temp_message_for_actions_edit = await message.answer(get_text("loading_text", lang, default="."), reply_markup=types.ReplyKeyboardRemove())
    mock_callback_for_actions = types.CallbackQuery(
        id=str(message.message_id) + "_actions_after_loc_val_recv", 
        from_user=message.from_user,
        chat_instance=str(message.chat.id),
        message=temp_message_for_actions_edit, 
        data=f"admin_location_actions:{location_id}"
    )
    await cq_admin_location_actions(mock_callback_for_actions, user_data, state)


@router.callback_query(F.data.startswith("admin_confirm_delete_location_prompt:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))
async def cq_admin_confirm_delete_location_prompt(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    location_id = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    location_name = state_data.get("current_location_name")

    if state_data.get("current_location_id") != location_id or not location_name:
        location_details = await location_service.get_location_details(location_id, lang)
        if not location_details:
            await callback.answer(get_text("admin_location_not_found_error", lang), show_alert=True)
            current_page = state_data.get("current_location_list_page", 0)
            return await _send_paginated_locations_list(callback, state, user_data, page=current_page)
        location_name = location_details['name']
        await state.update_data(current_location_id=location_id, current_location_name=location_name) 

    await state.set_state(AdminProductStates.LOCATION_CONFIRM_DELETE)
    
    confirmation_text = get_text("admin_confirm_delete_location_prompt", lang, name=location_name)
    keyboard = create_confirmation_keyboard(
        lang,
        yes_callback=f"admin_execute_delete_location:{location_id}",
        no_callback=f"admin_location_actions:{location_id}" 
    )
    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_execute_delete_location:"), StateFilter(AdminProductStates.LOCATION_CONFIRM_DELETE))
async def cq_admin_execute_delete_location(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    location_id = state_data.get("current_location_id") 
    location_name_from_state = state_data.get("current_location_name", "N/A")

    callback_location_id = int(callback.data.split(":")[1])
    if location_id != callback_location_id: 
        logger.warning(f"Location ID mismatch in delete execution. State: {location_id}, Callback: {callback_location_id}")
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        await state.clear() 
        return await _send_paginated_locations_list(callback, state, user_data, page=0)

    success, msg_key, deleted_loc_name = await location_service.delete_location_by_id(location_id, lang)
    
    display_name = deleted_loc_name or location_name_from_state 
    
    await callback.answer(get_text(msg_key, lang, name=display_name), show_alert=True)
    
    await state.clear() 
    await _send_paginated_locations_list(callback, state, user_data, page=0) # Refresh list


# --- Universal Cancel for Admin FSM Actions (Ensure Location States are Handled) ---
# The existing universal_cancel_admin_action should be reviewed to ensure it handles
# AdminProductStates.LOCATION_AWAIT_NAME, LOCATION_AWAIT_ADDRESS, 
# LOCATION_AWAIT_EDIT_NAME, LOCATION_AWAIT_EDIT_ADDRESS, LOCATION_CONFIRM_DELETE
# and navigates appropriately, likely back to cq_admin_locations_menu or cq_admin_location_actions.

# Example modification for universal_cancel_admin_action (conceptual)
# (Actual implementation might vary based on existing structure)
# if current_fsm_state_obj.startswith("AdminProductStates:LOCATION_"):
#     location_id_context = state_data.get("current_location_id")
#     if location_id_context and current_fsm_state_obj not in [AdminProductStates.LOCATION_AWAIT_NAME, AdminProductStates.LOCATION_AWAIT_ADDRESS]:
#         # If editing/deleting a specific location, go back to its actions menu
#         await state.set_state(AdminProductStates.LOCATION_SELECT_FOR_EDIT)
#         # Mock callback to cq_admin_location_actions
#         # ... (code to mock callback and call cq_admin_location_actions)
#         return
#     else: # Go to main location menu
#         target_message_text = get_text("admin_location_management_title", lang)
#         target_reply_markup = create_admin_location_management_menu_keyboard(lang)
#         # ... (code to send this message)
#     await state.clear()
#     return


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
            # Check if it's a location-specific state
            if "LOCATION_" in current_fsm_state_obj:
                location_id_context = state_data.get("current_location_id")
                # If in a sub-flow of a specific location (e.g. editing name/address, confirm delete)
                if location_id_context and current_fsm_state_obj not in [
                    AdminProductStates.LOCATION_AWAIT_NAME, # This is for global add, not specific edit
                    AdminProductStates.LOCATION_AWAIT_ADDRESS, # Global add
                    AdminProductStates.LOCATION_SELECT_FOR_EDIT, # This is the list view
                    AdminProductStates.LOCATION_SELECT_FOR_DELETE # Also list view (if used)
                ]:
                    await state.set_state(AdminProductStates.LOCATION_SELECT_FOR_EDIT)
                    temp_message_for_edit = await response_target.answer(get_text("loading_text", lang, default="."), reply_markup=types.ReplyKeyboardRemove()) if not isinstance(event, types.CallbackQuery) else event.message
                    
                    mock_cb_data = f"admin_location_actions:{location_id_context}"
                    await cq_admin_location_actions(
                        types.CallbackQuery(
                            id=str(event.id) + "_cancel_to_loc_actions", 
                            from_user=event.from_user, 
                            chat_instance=event.chat.id if hasattr(event, 'chat') else event.message.chat.id, 
                            message=temp_message_for_edit, # Use the message that can be edited
                            data=mock_cb_data
                        ),
                        user_data, state
                    )
                    return
                else: # Global location states (add name/address, list view) -> go to location menu
                    target_message_text = get_text("admin_location_management_title", lang)
                    target_reply_markup = create_admin_location_management_menu_keyboard(lang)
            elif "MANUFACTURER_" in current_fsm_state_obj: # Example for manufacturer
                # Similar logic for manufacturer if needed, e.g., go to manufacturer menu
                target_message_text = get_text("admin_manufacturer_management_title", lang) # Assuming this key exists
                target_reply_markup = create_admin_manufacturer_management_menu_keyboard(lang)
            else: # Default for other product states (e.g. product, category)
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

# --- Manufacturer Delete Handlers ---
async def _send_paginated_manufacturers_for_delete(
    event: Union[types.Message, types.CallbackQuery], 
    state: FSMContext, 
    user_data: Dict[str, Any], 
    page: int = 0
):
    lang = user_data.get("language", "en")
    product_service = ProductService()
    user_service = UserService()

    if not await is_admin_user_check(event.from_user.id, user_service):
        msg = get_text("admin_access_denied", lang)
        if isinstance(event, types.CallbackQuery): await event.answer(msg, show_alert=True)
        else: await event.answer(msg)
        return

    manufacturers_on_page_data, total_manufacturers = await product_service.get_all_entities_paginated(
        entity_type="manufacturer", 
        page=page, 
        items_per_page=ITEMS_PER_PAGE_ADMIN, 
        language=lang
    )

    title = get_text("admin_select_manufacturer_to_delete_title", lang)

    if not manufacturers_on_page_data and page == 0:
        empty_text = title + "\n\n" + get_text("admin_no_manufacturers_to_delete", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_manufacturer_menu", lang, "admin_manufacturers_menu")).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
             await target_message.edit_text(empty_text, reply_markup=kb)
        else:
             await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery): await event.answer()
        return

    await state.set_state(AdminProductStates.MANUFACTURER_SELECT_FOR_DELETE)
    await state.update_data(current_manufacturer_delete_page=page)

    keyboard = create_paginated_keyboard(
        items=manufacturers_on_page_data,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_select_manufacturer_for_delete_page",
        item_callback_prefix="admin_confirm_delete_manufacturer_prompt",
        language=lang,
        back_callback_key="back_to_manufacturer_menu",
        back_callback_data="admin_manufacturers_menu",
        total_items_override=total_manufacturers,
        item_text_key="name",
        item_id_key="id"
    )
    
    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
        await target_message.edit_text(title, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target_message.answer(title, reply_markup=keyboard, parse_mode="HTML")
        
    if isinstance(event, types.CallbackQuery): await event.answer()

@router.callback_query(F.data == "admin_delete_manufacturer_start", StateFilter("*")) # Accessible from manufacturer menu
async def cq_admin_select_manufacturer_for_delete(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    await _send_paginated_manufacturers_for_delete(callback, state, user_data, page=0)

@router.callback_query(F.data.startswith("admin_select_manufacturer_for_delete_page:"), StateFilter(AdminProductStates.MANUFACTURER_SELECT_FOR_DELETE))
async def cq_admin_select_manufacturer_for_delete_paginate(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    page = int(callback.data.split(":")[1])
    await _send_paginated_manufacturers_for_delete(callback, state, user_data, page=page)

@router.callback_query(F.data.startswith("admin_confirm_delete_manufacturer_prompt:"), StateFilter(AdminProductStates.MANUFACTURER_SELECT_FOR_DELETE))
async def cq_admin_confirm_delete_manufacturer_prompt(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    product_service = ProductService()
    user_service = UserService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    manufacturer_id = int(callback.data.split(":")[1])
    
    manufacturer_entity = await product_service.get_entity_by_id("manufacturer", manufacturer_id, lang)
    if not manufacturer_entity:
        await callback.answer(get_text("admin_manufacturer_not_found", lang), show_alert=True)
        # Go back to the selection list
        current_page = (await state.get_data()).get("current_manufacturer_delete_page", 0)
        return await _send_paginated_manufacturers_for_delete(callback, state, user_data, page=current_page)

    manufacturer_name = manufacturer_entity.get("name", str(manufacturer_id))
    
    await state.set_state(AdminProductStates.MANUFACTURER_CONFIRM_DELETE)
    await state.update_data(manufacturer_to_delete_id=manufacturer_id, manufacturer_to_delete_name=manufacturer_name)

    confirmation_text = get_text("admin_confirm_delete_manufacturer_prompt", lang, name=manufacturer_name)
    keyboard = create_confirmation_keyboard(
        lang,
        yes_callback=f"admin_execute_delete_manufacturer:{manufacturer_id}",
        no_callback="admin_delete_manufacturer_start" # Back to list selection start
    )
    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_execute_delete_manufacturer:"), StateFilter(AdminProductStates.MANUFACTURER_CONFIRM_DELETE))
async def cq_admin_execute_delete_manufacturer(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    product_service = ProductService()
    user_service = UserService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    manufacturer_id = state_data.get("manufacturer_to_delete_id")
    manufacturer_name = state_data.get("manufacturer_to_delete_name", "N/A") # Fallback name

    # Verify callback data matches state data as a safeguard
    callback_manufacturer_id = int(callback.data.split(":")[1])
    if manufacturer_id != callback_manufacturer_id:
        logger.warning(f"Manufacturer ID mismatch in delete execution. State: {manufacturer_id}, Callback: {callback_manufacturer_id}")
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        await state.clear()
        return await _send_paginated_manufacturers_for_delete(callback, state, user_data, page=0) # Refresh list

    success, message_key, deleted_name = await product_service.delete_manufacturer_by_id(manufacturer_id, lang)
    
    display_name = deleted_name or manufacturer_name # Use name from service if available, else from state

    if message_key == "admin_manufacturer_deleted_successfully":
        alert_text = get_text(message_key, lang, name=display_name)
    elif message_key == "admin_manufacturer_delete_has_products_error":
        alert_text = get_text(message_key, lang, name=display_name)
    elif message_key == "admin_manufacturer_delete_failed":
         alert_text = get_text(message_key, lang, name=display_name)
    else: # admin_manufacturer_not_found or other generic errors
        alert_text = get_text(message_key, lang)

    await callback.answer(alert_text, show_alert=True)
    
    await state.clear() # Clear state after operation
    # Refresh the list of manufacturers to delete
    await _send_paginated_manufacturers_for_delete(callback, state, user_data, page=0)


# --- Handler Registration (Illustrative - Actual registration in main bot file) ---
# router.callback_query(F.data == "admin_delete_manufacturer_start", StateFilter("*"))(cq_admin_select_manufacturer_for_delete)
# router.callback_query(F.data.startswith("admin_select_manufacturer_for_delete_page:"), StateFilter(AdminProductStates.MANUFACTURER_SELECT_FOR_DELETE))(cq_admin_select_manufacturer_for_delete_paginate)
# router.callback_query(F.data.startswith("admin_confirm_delete_manufacturer_prompt:"), StateFilter(AdminProductStates.MANUFACTURER_SELECT_FOR_DELETE))(cq_admin_confirm_delete_manufacturer_prompt)
# router.callback_query(F.data.startswith("admin_execute_delete_manufacturer:"), StateFilter(AdminProductStates.MANUFACTURER_CONFIRM_DELETE))(cq_admin_execute_delete_manufacturer)

# --- Location Handler Registration (Illustrative) ---
# router.callback_query(F.data == "admin_locations_menu", StateFilter("*"))(cq_admin_locations_menu)
# router.callback_query(F.data == "admin_add_location_start", StateFilter("*"))(cq_admin_add_location_start)
# router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_NAME), F.text)(fsm_admin_location_name_received)
# router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_ADDRESS), F.text)(fsm_admin_location_address_received)
# router.callback_query(F.data.startswith("admin_list_locations_start") | F.data.startswith("admin_locations_list_page:"))(cq_admin_list_locations_start)
# router.callback_query(F.data.startswith("admin_location_actions:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_location_actions)
# router.callback_query(F.data.startswith("admin_edit_location_start:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_edit_location_start)
# router.callback_query(F.data.startswith("admin_edit_location_field:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_edit_location_field_prompt)
# router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_EDIT_NAME, AdminProductStates.LOCATION_AWAIT_EDIT_ADDRESS), F.text)(fsm_admin_location_edit_value_received)
# router.callback_query(F.data.startswith("admin_confirm_delete_location_prompt:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_confirm_delete_location_prompt)
# router.callback_query(F.data.startswith("admin_execute_delete_location:"), StateFilter(AdminProductStates.LOCATION_CONFIRM_DELETE))(cq_admin_execute_delete_location)


# --- Location Management Handlers ---

@router.callback_query(F.data == "admin_locations_menu", StateFilter("*"))
async def cq_admin_locations_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    await state.clear() # Clear state when entering the menu
    # Assuming create_admin_location_management_menu_keyboard will be defined in app.keyboards.inline
    from app.keyboards.inline import create_admin_location_management_menu_keyboard 
    keyboard = create_admin_location_management_menu_keyboard(lang) 
    await callback.message.edit_text(get_text("admin_location_management_title", lang), reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "admin_add_location_start", StateFilter("*"))
async def cq_admin_add_location_start(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    await state.set_state(AdminProductStates.LOCATION_AWAIT_NAME)
    prompt_text = get_text("admin_enter_location_name_prompt", lang)
    cancel_info = get_text("cancel_prompt", lang)
    await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")
    await callback.answer()

@router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_NAME), F.text)
async def fsm_admin_location_name_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        return await universal_cancel_admin_action(message, state, user_data)

    name = sanitize_input(message.text)
    if not name:
        await message.answer(get_text("admin_location_name_empty_error", lang))
        # Re-prompt
        prompt_text = get_text("admin_enter_location_name_prompt", lang)
        cancel_info = get_text("cancel_prompt", lang)
        await message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")
        return

    await state.update_data(location_name=name)
    await state.set_state(AdminProductStates.LOCATION_AWAIT_ADDRESS)
    prompt_text = get_text("admin_enter_location_address_prompt", lang)
    cancel_info = get_text("cancel_prompt", lang)
    await message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")

@router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_ADDRESS), F.text)
async def fsm_admin_location_address_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        return await universal_cancel_admin_action(message, state, user_data)

    address = sanitize_input(message.text)
    if address == "-": # Treat '-' as skip/None for address
        address = None
    
    state_data = await state.get_data()
    name = state_data.get("location_name")

    if not name: # Should not happen if flow is correct
        await message.answer(get_text("admin_action_failed_no_context", lang))
        await state.clear()
        # Navigate back to main admin panel or location menu
        from app.keyboards.inline import create_admin_location_management_menu_keyboard
        keyboard = create_admin_location_management_menu_keyboard(lang)
        await message.answer(get_text("admin_location_management_title", lang), reply_markup=keyboard)
        return

    location_dict, error_message_key = await location_service.create_location(name, address, lang)

    if location_dict:
        await message.answer(get_text("admin_location_created_successfully", lang, name=location_dict['name']))
    else:
        await message.answer(get_text(error_message_key or "admin_location_create_failed_error", lang, name=name))
    
    await state.clear()
    # Send locations menu again
    from app.keyboards.inline import create_admin_location_management_menu_keyboard
    keyboard = create_admin_location_management_menu_keyboard(lang)
    # This message will be a new message, not an edit of a callback query message
    await message.answer(get_text("admin_location_management_title", lang), reply_markup=keyboard)


async def _send_paginated_locations_list(
    event: Union[types.Message, types.CallbackQuery],
    state: FSMContext,
    user_data: Dict[str, Any],
    page: int = 0
):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()

    if not await is_admin_user_check(event.from_user.id, user_service):
        msg = get_text("admin_access_denied", lang)
        if isinstance(event, types.CallbackQuery): await event.answer(msg, show_alert=True)
        else: await event.answer(msg)
        return

    formatted_locations, total_count = await location_service.get_all_locations_paginated(
        page, ITEMS_PER_PAGE_ADMIN, lang
    )

    title = get_text("admin_locations_list_title", lang)

    if not formatted_locations and page == 0:
        empty_text = title + "\n\n" + get_text("admin_no_locations_found", lang)
        # Assuming create_admin_location_management_menu_keyboard exists for back button
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_location_menu", lang, "admin_locations_menu")).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
            await target_message.edit_text(empty_text, reply_markup=kb)
        else:
            await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery): await event.answer()
        return

    await state.set_state(AdminProductStates.LOCATION_SELECT_FOR_EDIT) 
    await state.update_data(current_location_list_page=page)

    keyboard = create_paginated_keyboard(
        items=formatted_locations,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_locations_list_page", 
        item_callback_prefix="admin_location_actions",
        language=lang,
        back_callback_key="back_to_location_menu", # Text key for the back button
        back_callback_data="admin_locations_menu", # Callback data for back button
        total_items_override=total_count,
        item_text_key="display_name", # Key from formatted_locations dict for button text
        item_id_key="id" # Key from formatted_locations dict for item ID in callback
    )
    
    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
        await target_message.edit_text(title, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target_message.answer(title, reply_markup=keyboard, parse_mode="HTML")
        
    if isinstance(event, types.CallbackQuery): await event.answer()


@router.callback_query(F.data.startswith("admin_list_locations_start") | F.data.startswith("admin_locations_list_page:"))
async def cq_admin_list_locations_start(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    page = 0
    # Callback data can be "admin_list_locations_start" or "admin_locations_list_page:PAGENUM"
    if callback.data.startswith("admin_locations_list_page:"):
        try:
            page = int(callback.data.split(":")[1])
        except (IndexError, ValueError): # Handle cases like "admin_locations_list_page:" without number
            page = 0 
    await _send_paginated_locations_list(callback, state, user_data, page=page)


@router.callback_query(F.data.startswith("admin_location_actions:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))
async def cq_admin_location_actions(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    location_service = LocationService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    location_id = int(callback.data.split(":")[1])
    location_details = await location_service.get_location_details(location_id, lang)

    if not location_details:
        await callback.answer(get_text("admin_location_not_found_error", lang), show_alert=True)
        current_page = (await state.get_data()).get("current_location_list_page", 0)
        # Need to pass the original callback event to _send_paginated_locations_list
        return await _send_paginated_locations_list(callback, state, user_data, page=current_page)

    await state.update_data(
        current_location_id=location_id, 
        current_location_name=location_details['name'],
        # Ensure address is stored, even if it's the placeholder for "Not specified"
        current_location_address=location_details.get('address', get_text("not_specified_placeholder", lang))
    )
    
    details_text = get_text("admin_location_details_display", lang, 
                            name=location_details['name'], 
                            address=location_details.get('address', get_text("not_specified_placeholder", lang)))
    
    # Assuming create_admin_location_item_actions_keyboard will be defined in app.keyboards.inline
    from app.keyboards.inline import create_admin_location_item_actions_keyboard 
    keyboard = create_admin_location_item_actions_keyboard(location_id, lang) 

    await callback.message.edit_text(details_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
"""
Admin handlers for order management, product administration, and system monitoring.
Only accessible to users with admin privileges.
Includes handlers for Product, Category, Manufacturer, Location and Stock management.
Order management includes: viewing orders, approving, rejecting, cancelling, changing status.
User management includes: listing, viewing details, blocking, unblocking.
Basic settings view and statistics display.
"""

import logging
from typing import Any, Dict, List, Optional, Union
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
    PRODUCT_AWAIT_EDIT_FIELD_VALUE = State() # State when edit options are shown
    PRODUCT_SELECT_ENTITY_FOR_FIELD = State() # State for selecting Manufacturer/Category during edit

    # Specific states for awaiting new values for each field during edit
    PRODUCT_AWAIT_NEW_COST = State()
    PRODUCT_AWAIT_NEW_SKU = State()
    PRODUCT_AWAIT_NEW_VARIATION = State()
    PRODUCT_AWAIT_NEW_IMAGE_URL = State()

    # States for managing localizations of an existing product
    PRODUCT_MANAGE_LOCALIZATIONS = State() # When localization action keyboard is shown
    PRODUCT_SELECT_NEW_LOCALIZATION_LANG = State() # When choosing a language to add a new localization for an existing product
    # PRODUCT_AWAIT_LOCALIZATION_NAME and PRODUCT_AWAIT_LOCALIZATION_DESCRIPTION are re-used

    # States for managing localizations of an existing product
    PRODUCT_MANAGE_LOCALIZATIONS = State() # When localization action keyboard is shown
    PRODUCT_SELECT_NEW_LOCALIZATION_LANG = State() # When choosing a language to add a new localization for an existing product
    # PRODUCT_AWAIT_LOCALIZATION_NAME and PRODUCT_AWAIT_LOCALIZATION_DESCRIPTION are re-used
    PRODUCT_CONFIRM_DELETE = State() # For confirming product deletion

    CATEGORY_AWAIT_NAME = State()
    CATEGORY_AWAIT_EDIT_NAME = State() 
    CATEGORY_SELECT_FOR_EDIT = State() 
    CATEGORY_SELECT_FOR_DELETE = State()

    MANUFACTURER_AWAIT_NAME = State()
    MANUFACTURER_AWAIT_EDIT_NAME = State()
    MANUFACTURER_SELECT_FOR_EDIT = State()
    MANUFACTURER_SELECT_FOR_DELETE = State()
    MANUFACTURER_CONFIRM_DELETE = State() # New state
    # MANUFACTURER_AWAIT_NEW_NAME = State() # Covered by MANUFACTURER_AWAIT_EDIT_NAME

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


# --- Helper for paginated entity selection for Product Creation ---
async def _send_paginated_entities_for_selection(
    event: Union[types.Message, types.CallbackQuery],
    state: FSMContext,
    user_data: Dict[str, Any],
    entity_type: str, # "manufacturer" or "category"
    page: int = 0,
    # Allow overriding some create_paginated_keyboard parameters for flexibility (used in product edit)
    item_callback_prefix_override: Optional[str] = None,
    base_pagination_cb_override: Optional[str] = None, 
    back_callback_key_override: Optional[str] = None,
    back_callback_data_override: Optional[str] = None,
    additional_buttons_override: Optional[List[List[InlineKeyboardButton]]] = None
):
    lang = user_data.get("language", "en")
    product_service = ProductService() # Using ProductService to fetch entities
    user_service = UserService()

    if not await is_admin_user_check(event.from_user.id, user_service):
        msg = get_text("admin_access_denied", lang)
        if isinstance(event, types.CallbackQuery): await event.answer(msg, show_alert=True)
        else: await event.answer(msg)
        return

    entities_on_page_data, total_entities = await product_service.get_all_entities_paginated(
        entity_type=entity_type,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        language=lang
    )

    title_key = f"admin_prod_enter_{entity_type}_id" # e.g., admin_prod_enter_manufacturer_id
    title = get_text(title_key, lang)
    
    # Add instruction about skipping category selection
    if entity_type == "category":
        title += "\n\n" + hitalic(get_text("admin_prod_category_skip_instruction", lang))


    if not entities_on_page_data and page == 0 and entity_type == "manufacturer": # Manufacturer is mandatory
        empty_text = title + "\n\n" + get_text(f"admin_no_{entity_type}s_found_for_product_creation", lang, entity=entity_type)
        # Back to product management menu if no manufacturers to select
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_product_management", lang, "admin_products_menu")).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
             await target_message.edit_text(empty_text, reply_markup=kb)
        else:
             await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery): await event.answer()
        return
    
    # For categories, if none are found, it's fine, user can skip.
    # The keyboard will show a "Skip" button in this case if entity_type is category.

    current_fsm_state = AdminProductStates.PRODUCT_AWAIT_MANUFACTURER_ID
    item_callback_prefix = item_callback_prefix_override or ("admin_prod_create_select_manufacturer" if entity_type == "manufacturer" else "admin_prod_create_select_category")
    base_pagination_cb = base_pagination_cb_override or ("admin_prod_create_page_manufacturer" if entity_type == "manufacturer" else "admin_prod_create_page_category")
    
    current_fsm_state_for_selection = AdminProductStates.PRODUCT_AWAIT_MANUFACTURER_ID # Default for create
    if "admin_prod_create" in item_callback_prefix: # Explicitly check if it's for creation flow
        if entity_type == "category":
            current_fsm_state_for_selection = AdminProductStates.PRODUCT_AWAIT_CATEGORY_ID
    elif "admin_prod_edit" in item_callback_prefix: # Explicitly check if it's for edit flow
        current_fsm_state_for_selection = AdminProductStates.PRODUCT_SELECT_ENTITY_FOR_FIELD
    # else: log warning or default, for now this covers the known cases

    await state.set_state(current_fsm_state_for_selection)
    await state.update_data({f"current_{entity_type}_selection_page": page}) 

    final_additional_buttons = additional_buttons_override
    # Default skip button for category creation if no override is provided
    if entity_type == "category" and "create" in item_callback_prefix and additional_buttons_override is None:
        final_additional_buttons = [[InlineKeyboardButton(text=get_text("skip", lang), callback_data=f"{item_callback_prefix}:skip")]]
    # For category edit, additional_buttons_override will be used if provided (e.g. "Skip and Remove")


    keyboard = create_paginated_keyboard(
        items=entities_on_page_data, 
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=base_pagination_cb, 
        item_callback_prefix=item_callback_prefix, 
        language=lang,
        back_callback_key=back_callback_key_override or "cancel_add_product", 
        back_callback_data=back_callback_data_override or "admin_prod_add_cancel_to_menu",
        total_items_override=total_entities,
        item_text_key="name",
        item_id_key="id",
        additional_buttons=final_additional_buttons
    )
    
    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
        await target_message.edit_text(title, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Remove reply keyboard if any previous message handler left one
        await target_message.answer(title, reply_markup=keyboard, parse_mode="HTML")
        
    if isinstance(event, types.CallbackQuery): await event.answer()


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

# --- Product Management Menu Handler ---
@router.callback_query(F.data == "admin_products_menu", StateFilter("*"))
async def cq_admin_products_menu(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    keyboard = create_admin_product_management_menu_keyboard(lang)
    await callback.message.edit_text(get_text("admin_product_management_title", lang), reply_markup=keyboard)
    await callback.answer()

# --- Stock Management Menu Handler ---
@router.callback_query(F.data == "admin_stock_menu", StateFilter("*"))
async def cq_admin_stock_menu(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    # Assuming "admin_stock_management_title" text key exists or will be added.
    # Using "Stock Management" as a placeholder if the key is missing, as per instructions.
    title_text = get_text("admin_stock_management_title", lang, default="Stock Management")
    keyboard = create_admin_stock_management_menu_keyboard(lang)
    
    try:
        await callback.message.edit_text(title_text, reply_markup=keyboard)
    except Exception as e: # Fallback if edit fails (e.g. message not modified)
        logger.info(f"Editing message for admin_stock_menu failed, sending new: {e}")
        await callback.message.answer(title_text, reply_markup=keyboard)
        
    await callback.answer()

# --- Manufacturer Management Menu Handler ---
@router.callback_query(F.data == "admin_manufacturers_menu", StateFilter("*"))
async def cq_admin_manufacturers_main_menu(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    title_text = get_text("admin_manufacturer_management_title", lang, default="Manufacturer Management")
    keyboard = create_admin_manufacturer_management_menu_keyboard(lang)
    
    try:
        await callback.message.edit_text(title_text, reply_markup=keyboard)
    except Exception as e:
        logger.info(f"Editing message for admin_manufacturers_menu failed, sending new: {e}")
        await callback.message.answer(title_text, reply_markup=keyboard)
        
    await callback.answer()

# --- Category Management Menu Handler ---
@router.callback_query(F.data == "admin_categories_menu", StateFilter("*"))
async def cq_admin_categories_menu(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    await state.clear()
    title_text = get_text("admin_category_management_title", lang, default="Category Management")
    keyboard = create_admin_category_management_menu_keyboard(lang)
    
    try:
        await callback.message.edit_text(title_text, reply_markup=keyboard)
    except Exception as e:
        logger.info(f"Editing message for admin_categories_menu failed, sending new: {e}")
        await callback.message.answer(title_text, reply_markup=keyboard)
        
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
                 # The new if block goes here
                 if current_fsm_state_obj in [
                     AdminProductStates.PRODUCT_AWAIT_MANUFACTURER_ID,
                     AdminProductStates.PRODUCT_AWAIT_CATEGORY_ID,
                     AdminProductStates.PRODUCT_AWAIT_COST,
                     AdminProductStates.PRODUCT_AWAIT_SKU,
                     AdminProductStates.PRODUCT_AWAIT_VARIATION,
                     AdminProductStates.PRODUCT_AWAIT_IMAGE_URL,
                     AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_LANG_CODE,
                     AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_NAME,
                     AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_DESCRIPTION,
                     AdminProductStates.PRODUCT_CONFIRM_ADD
                 ]:
                     # If cancelling during product creation, go to product management menu
                     target_message_text = get_text("admin_product_management_title", lang)
                     target_reply_markup = create_admin_product_management_menu_keyboard(lang)
                 elif current_fsm_state_obj.startswith("AdminProductStates:"): # Catch-all for other product states
                     # Default for other product states (e.g. product, category, manufacturer)
                     # Navigate to product management menu
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

# --- Manufacturer Add Handlers ---
@router.callback_query(F.data == "admin_mfg_add_start", StateFilter("*"))
async def cq_admin_mfg_add_start(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    await state.set_state(AdminProductStates.MANUFACTURER_AWAIT_NAME)
    
    prompt_text = get_text("admin_mfg_enter_name_prompt", lang, default="Please enter the name for the new manufacturer:")
    cancel_info = get_text("cancel_prompt", lang)
    
    full_prompt = f"{prompt_text}\n\n{hitalic(cancel_info)}"
    
    try:
        await callback.message.edit_text(full_prompt, parse_mode="HTML", reply_markup=None) # Remove previous keyboard
    except Exception as e:
        logger.info(f"Editing message for admin_mfg_add_start failed, sending new: {e}")
        # Send as a new message if edit fails, ensuring ReplyKeyboardRemove to clear any prior reply keyboards
        await callback.message.answer(full_prompt, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
        
    await callback.answer()

@router.message(StateFilter(AdminProductStates.MANUFACTURER_AWAIT_NAME), F.text)
async def fsm_admin_manufacturer_name_received(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()

    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        await message.answer(get_text("admin_action_cancelled", lang), reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        # Directly send manufacturer menu
        keyboard = create_admin_manufacturer_management_menu_keyboard(lang)
        title_text = get_text("admin_manufacturer_management_title", lang, default="Manufacturer Management")
        await message.answer(title_text, reply_markup=keyboard, parse_mode="HTML")
        return

    sanitized_name = sanitize_input(message.text)

    if not sanitized_name:
        error_msg = get_text("admin_mfg_name_empty_error", lang, default="Manufacturer name cannot be empty. Please try again.")
        prompt_text = get_text("admin_mfg_enter_name_prompt", lang, default="Please enter the name for the new manufacturer:")
        cancel_info = get_text("cancel_prompt", lang)
        full_reprompt = f"{error_msg}\n\n{prompt_text}\n\n{hitalic(cancel_info)}"
        await message.answer(full_reprompt, parse_mode="HTML")
        return

    product_service = ProductService()
    created_manufacturer, message_key, _ = await product_service.create_manufacturer(name=sanitized_name, lang=lang)

    if created_manufacturer:
        success_msg = get_text(message_key, lang, name=hcode(created_manufacturer['name']))
        await message.answer(success_msg, parse_mode="HTML")
    else:
        # message_key here would be an error string like "admin_mfg_already_exists_error"
        # or "admin_mfg_create_failed_error"
        error_msg = get_text(message_key, lang, name=hcode(sanitized_name))
        await message.answer(error_msg, parse_mode="HTML")

    await state.clear()
    
    # Directly send manufacturer menu
    keyboard = create_admin_manufacturer_management_menu_keyboard(lang)
    title_text = get_text("admin_manufacturer_management_title", lang, default="Manufacturer Management")
    await message.answer(title_text, reply_markup=keyboard, parse_mode="HTML")


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


# --- Manufacturer Edit Handlers ---

async def _send_paginated_manufacturers_for_edit(
    event: Union[types.Message, types.CallbackQuery],
    state: FSMContext,
    user_data: Dict[str, Any],
    page: int = 0,
    # Allow overriding some create_paginated_keyboard parameters for flexibility
    item_callback_prefix_override: Optional[str] = None,
    back_callback_key_override: Optional[str] = None,
    back_callback_data_override: Optional[str] = None,
    base_callback_data_override: Optional[str] = None # For pagination callback base
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

    title = get_text("admin_select_manufacturer_to_edit_title", lang)

    if not manufacturers_on_page_data and page == 0:
        empty_text = title + "\n\n" + get_text("admin_no_manufacturers_found", lang) # Using generic "no manufacturers found"
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_manufacturer_menu", lang, "admin_manufacturers_menu")).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
             await target_message.edit_text(empty_text, reply_markup=kb)
        else:
             await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery): await event.answer()
        return

    await state.set_state(AdminProductStates.MANUFACTURER_SELECT_FOR_EDIT)
    await state.update_data(current_manufacturer_edit_page=page)

    keyboard = create_paginated_keyboard(
        items=manufacturers_on_page_data,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data="admin_select_manufacturer_for_edit_page",
        item_callback_prefix="admin_edit_manufacturer_prompt", # Action for selecting a manufacturer to edit
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

@router.callback_query(F.data == "admin_edit_manufacturer_start", StateFilter("*"))
async def cq_admin_edit_manufacturer_start(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    await _send_paginated_manufacturers_for_edit(callback, state, user_data, page=0)

@router.callback_query(F.data.startswith("admin_select_manufacturer_for_edit_page:"), StateFilter(AdminProductStates.MANUFACTURER_SELECT_FOR_EDIT))
async def cq_admin_select_manufacturer_for_edit_paginate(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 0 # Default to page 0 if malformed
    await _send_paginated_manufacturers_for_edit(callback, state, user_data, page=page)

@router.callback_query(F.data.startswith("admin_edit_manufacturer_prompt:"), StateFilter(AdminProductStates.MANUFACTURER_SELECT_FOR_EDIT))
async def cq_admin_edit_manufacturer_prompt_name(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    product_service = ProductService()
    user_service = UserService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        manufacturer_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        return # Or redirect to list

    manufacturer_entity = await product_service.get_entity_by_id("manufacturer", manufacturer_id, lang)
    if not manufacturer_entity:
        await callback.answer(get_text("admin_manufacturer_not_found", lang), show_alert=True)
        current_page = (await state.get_data()).get("current_manufacturer_edit_page", 0)
        return await _send_paginated_manufacturers_for_edit(callback, state, user_data, page=current_page)

    current_name = manufacturer_entity.get("name", str(manufacturer_id))
    
    await state.set_state(AdminProductStates.MANUFACTURER_AWAIT_EDIT_NAME)
    await state.update_data(editing_manufacturer_id=manufacturer_id, editing_manufacturer_current_name=current_name)

    prompt_text = get_text("admin_enter_new_manufacturer_name_prompt", lang, current_name=hcode(current_name))
    cancel_info = get_text("cancel_prompt", lang)
    
    # Provide a back button to go back to the selection list
    # Back button to go back to the selection list, preserving the page
    current_page = (await state.get_data()).get("current_manufacturer_edit_page", 0)
    back_button_cb = f"admin_select_manufacturer_for_edit_page:{current_page}"
    if callback.data == "admin_edit_manufacturer_start": # If came from menu directly, no page, go to page 0
        back_button_cb = "admin_edit_manufacturer_start"


    builder = InlineKeyboardBuilder()
    # builder.row(create_back_button("back_to_manufacturer_selection", lang, back_button_cb)) # TODO: This back button might be tricky with message edits. For now, rely on /cancel.
    
    await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.message(StateFilter(AdminProductStates.MANUFACTURER_AWAIT_EDIT_NAME), F.text)
async def fsm_admin_manufacturer_new_name_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    product_service = ProductService()
    user_service = UserService()

    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        # Before calling universal cancel, determine the correct "back" navigation
        # Send them back to the manufacturer edit selection list
        await message.answer(get_text("admin_action_cancelled", lang)) # Acknowledge cancel first
        state_data = await state.get_data()
        current_page = state_data.get("current_manufacturer_edit_page", 0)
        # We need a CallbackQuery-like object or to call the list function directly with a message
        # For simplicity, create a mock message event and call the list function.
        # This is a bit of a workaround because universal_cancel might not be ideal here.
        await state.clear() # Clear state first
         # Create a temporary message to be edited by the paginated list function
        temp_msg_for_list = await message.answer(get_text("loading_text", lang))
        mock_event_for_list = temp_msg_for_list # It can take a message directly
        return await _send_paginated_manufacturers_for_edit(mock_event_for_list, state, user_data, page=current_page)


    state_data = await state.get_data()
    manufacturer_id = state_data.get("editing_manufacturer_id")
    original_name = state_data.get("editing_manufacturer_current_name")

    if not manufacturer_id or original_name is None:
        await message.answer(get_text("admin_action_failed_no_context", lang))
        await state.clear()
        # Send back to main manufacturers menu
        return await cq_admin_manufacturers_menu_entry_point(message, state, user_data) # Assuming such a function exists or create one

    new_name = sanitize_input(message.text)

    if not new_name:
        await message.answer(get_text("admin_manufacturer_name_empty_error", lang))
        prompt_text = get_text("admin_enter_new_manufacturer_name_prompt", lang, current_name=hcode(original_name))
        cancel_info = get_text("cancel_prompt", lang)
        await message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML") # Re-prompt
        return

    if new_name == original_name:
        await message.answer(get_text("admin_manufacturer_name_not_changed_error", lang, name=hcode(original_name)))
        # Optionally, re-prompt or offer cancel. For now, just inform.
        # To re-prompt:
        # prompt_text = get_text("admin_enter_new_manufacturer_name_prompt", lang, current_name=hcode(original_name))
        # cancel_info = get_text("cancel_prompt", lang)
        # await message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")
        # return
        # For now, we will proceed to send them back to the list after this message.
        # Fall through to sending back to list.

    success, msg_key, updated_details = await product_service.update_manufacturer_details(manufacturer_id, new_name, lang)

    if success and updated_details:
        await message.answer(get_text(msg_key, lang, name=hcode(updated_details['name'])))
    else:
        # Use original_name for context in error messages if new_name failed (e.g. duplicate)
        await message.answer(get_text(msg_key, lang, name=hcode(new_name), original_name=hcode(original_name)))

    await state.clear()
    current_page = state_data.get("current_manufacturer_edit_page", 0)
    # Send back to the list of manufacturers for editing.
    # Create a temporary message that _send_paginated_manufacturers_for_edit can edit or reply to.
    temp_msg_for_list_after_edit = await message.answer(get_text("loading_text", lang))
    await _send_paginated_manufacturers_for_edit(temp_msg_for_list_after_edit, state, user_data, page=current_page)


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
# router.callback_query(F.data.startswith("admin_location_actions:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_location_actions) # type: ignore
# router.callback_query(F.data.startswith("admin_edit_location_start:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_edit_location_start) # type: ignore
# router.callback_query(F.data.startswith("admin_edit_location_field:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_edit_location_field_prompt) # type: ignore
# router.message(StateFilter(AdminProductStates.LOCATION_AWAIT_EDIT_NAME, AdminProductStates.LOCATION_AWAIT_EDIT_ADDRESS), F.text)(fsm_admin_location_edit_value_received) # type: ignore
# router.callback_query(F.data.startswith("admin_confirm_delete_location_prompt:"), StateFilter(AdminProductStates.LOCATION_SELECT_FOR_EDIT))(cq_admin_confirm_delete_location_prompt)
# router.callback_query(F.data.startswith("admin_execute_delete_location:"), StateFilter(AdminProductStates.LOCATION_CONFIRM_DELETE))(cq_admin_execute_delete_location)


# --- Location Management Handlers ---

@router.callback_query(F.data == "admin_locations_menu", StateFilter("*"))
async def cq_admin_locations_menu(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext): # type: ignore
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
async def cq_admin_add_location_start(callback: types.CallbackQuery, user_data: Dict[str, Any], state: FSMContext): # type: ignore
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


# Placeholder for where cq_admin_manufacturers_menu would be if it's a separate entry point
async def cq_admin_manufacturers_menu_entry_point(message_or_callback: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any]):
    """Helper to navigate to the main manufacturer menu, e.g. after an action or cancel."""
    lang = user_data.get("language", "en")
    target_message = message_or_callback.message if isinstance(message_or_callback, types.CallbackQuery) else message_or_callback
    
    keyboard = create_admin_manufacturer_management_menu_keyboard(lang)
    text = get_text("admin_manufacturer_management_title", lang)
    
    # Clear state before navigating to a main menu
    await state.clear()

    if isinstance(message_or_callback, types.CallbackQuery) and hasattr(target_message, "edit_text"):
        try:
            await target_message.edit_text(text, reply_markup=keyboard)
        except Exception as e: # If edit fails, send new message
            logger.debug(f"Failed to edit message for cq_admin_manufacturers_menu_entry_point: {e}")
            await target_message.answer(text, reply_markup=keyboard)
    else:
        await target_message.answer(text, reply_markup=keyboard)
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.answer()


# --- Product Creation Handlers ---

@router.callback_query(F.data == "admin_prod_add_start", StateFilter("*"))
async def cq_admin_prod_add_start(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    # Clear any previous product creation data
    await state.update_data(product_data={}, product_localizations_temp=[])
    
    await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="manufacturer", page=0)

@router.callback_query(F.data == "admin_prod_add_cancel_to_menu", StateFilter(AdminProductStates)) # Universal cancel for this flow
async def cq_admin_prod_add_cancel_to_menu(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    await callback.answer(get_text("admin_action_cancelled", lang))
    await state.clear()
    
    # Go to Product Management Menu
    prod_menu_text = get_text("admin_product_management_title", lang)
    prod_menu_kb = create_admin_product_management_menu_keyboard(lang)
    await callback.message.edit_text(prod_menu_text, reply_markup=prod_menu_kb)


# Pagination for manufacturer selection during product creation
@router.callback_query(F.data.startswith("admin_prod_create_page_manufacturer:"), StateFilter(AdminProductStates.PRODUCT_AWAIT_MANUFACTURER_ID))
async def cq_admin_prod_create_page_manufacturer(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 0
    await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="manufacturer", page=page)

# Pagination for category selection during product creation
@router.callback_query(F.data.startswith("admin_prod_create_page_category:"), StateFilter(AdminProductStates.PRODUCT_AWAIT_CATEGORY_ID))
async def cq_admin_prod_create_page_category(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 0
    await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="category", page=page)


# Handler for selecting manufacturer during product creation
@router.callback_query(F.data.startswith("admin_prod_create_select_manufacturer:"), StateFilter(AdminProductStates.PRODUCT_AWAIT_MANUFACTURER_ID))
async def cq_admin_prod_create_select_manufacturer(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService() # To validate manufacturer exists

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        manufacturer_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        # Go back to manufacturer selection
        current_page = (await state.get_data()).get("current_manufacturer_selection_page", 0)
        return await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="manufacturer", page=current_page)

    # Verify manufacturer exists (important if list is somehow stale)
    manufacturer = await product_service.get_entity_by_id("manufacturer", manufacturer_id, lang)
    if not manufacturer:
        await callback.answer(get_text("admin_error_manufacturer_not_found_short", lang), show_alert=True) # Using a short version
        current_page = (await state.get_data()).get("current_manufacturer_selection_page", 0)
        return await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="manufacturer", page=current_page)

    current_product_data = (await state.get_data()).get("product_data", {})
    current_product_data["manufacturer_id"] = manufacturer_id
    current_product_data["manufacturer_name"] = manufacturer.get("name", str(manufacturer_id)) # Store name for summary
    await state.update_data(product_data=current_product_data)
    
    # Now ask for category
    await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="category", page=0)


# Handler for selecting category (or skipping) during product creation
@router.callback_query(F.data.startswith("admin_prod_create_select_category:"), StateFilter(AdminProductStates.PRODUCT_AWAIT_CATEGORY_ID))
async def cq_admin_prod_create_select_category(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService() # To validate category exists if not skipped

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    category_id_str = callback.data.split(":")[1]
    category_id = None
    category_name = get_text("not_applicable_short", lang) # Default if skipped

    if category_id_str.lower() == "skip":
        category_id = None
    else:
        try:
            category_id = int(category_id_str)
            # Verify category exists
            category = await product_service.get_entity_by_id("category", category_id, lang)
            if not category:
                await callback.answer(get_text("admin_error_category_not_found_short", lang), show_alert=True)
                current_page = (await state.get_data()).get("current_category_selection_page", 0)
                return await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="category", page=current_page)
            category_name = category.get("name", str(category_id))
        except ValueError:
            await callback.answer(get_text("error_occurred", lang), show_alert=True)
            current_page = (await state.get_data()).get("current_category_selection_page", 0)
            return await _send_paginated_entities_for_selection(callback, state, user_data, entity_type="category", page=current_page)

    current_product_data = (await state.get_data()).get("product_data", {})
    current_product_data["category_id"] = category_id # Will be None if skipped
    current_product_data["category_name"] = category_name # Store name for summary
    await state.update_data(product_data=current_product_data)

    await state.set_state(AdminProductStates.PRODUCT_AWAIT_COST)
    prompt_text = get_text("admin_prod_enter_cost", lang)
    cancel_info = get_text("cancel_prompt", lang)
    # Remove inline keyboard from previous message by sending a new one
    try: # Try to edit the existing message first to avoid clutter
        await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=None) # Remove kbd
    except Exception: # If edit fails (e.g. message too old or content unchanged), send new.
        await callback.message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await callback.answer() # Acknowledge the callback

# --- Message handlers for product data input ---

@router.message(StateFilter(AdminProductStates.PRODUCT_AWAIT_COST), F.text)
async def fsm_admin_prod_cost_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        # Create a mock callback to use the cancel flow that returns to product menu
        mock_callback = types.CallbackQuery(id=str(message.message_id)+"_cancel", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
        return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    try:
        cost = Decimal(sanitize_input(message.text))
        if cost <= 0:
            raise ValueError("Cost must be positive.")
    except (DecimalInvalidOperation, ValueError):
        await message.answer(get_text("admin_prod_invalid_cost_format", lang))
        # Re-prompt for cost
        prompt_text = get_text("admin_prod_enter_cost", lang)
        cancel_info = get_text("cancel_prompt", lang)
        await message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML")
        return

    current_product_data = (await state.get_data()).get("product_data", {})
    current_product_data["cost"] = str(cost)
    await state.update_data(product_data=current_product_data)

    await state.set_state(AdminProductStates.PRODUCT_AWAIT_SKU)
    prompt_text = get_text("admin_prod_enter_sku", lang)
    skip_info = get_text("admin_prod_skip_instruction_generic", lang)
    cancel_info = get_text("cancel_prompt", lang)
    await message.answer(f"{prompt_text}\n\n{hitalic(skip_info)}\n{hitalic(cancel_info)}", parse_mode="HTML")


@router.message(StateFilter(AdminProductStates.PRODUCT_AWAIT_SKU), F.text)
async def fsm_admin_prod_sku_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        mock_callback = types.CallbackQuery(id=str(message.message_id)+"_cancel", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
        return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    sku_input = sanitize_input(message.text)
    sku = sku_input if sku_input != "-" else None

    current_product_data = (await state.get_data()).get("product_data", {})
    current_product_data["sku"] = sku
    await state.update_data(product_data=current_product_data)

    await state.set_state(AdminProductStates.PRODUCT_AWAIT_VARIATION)
    prompt_text = get_text("admin_prod_enter_variation", lang)
    skip_info = get_text("admin_prod_skip_instruction_generic", lang)
    cancel_info = get_text("cancel_prompt", lang)
    await message.answer(f"{prompt_text}\n\n{hitalic(skip_info)}\n{hitalic(cancel_info)}", parse_mode="HTML")


@router.message(StateFilter(AdminProductStates.PRODUCT_AWAIT_VARIATION), F.text)
async def fsm_admin_prod_variation_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        mock_callback = types.CallbackQuery(id=str(message.message_id)+"_cancel", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
        return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    variation_input = sanitize_input(message.text)
    variation = variation_input if variation_input != "-" else None

    current_product_data = (await state.get_data()).get("product_data", {})
    current_product_data["variation"] = variation
    await state.update_data(product_data=current_product_data)

    await state.set_state(AdminProductStates.PRODUCT_AWAIT_IMAGE_URL)
    prompt_text = get_text("admin_prod_enter_image_url", lang)
    skip_info = get_text("admin_prod_skip_instruction_generic", lang)
    cancel_info = get_text("cancel_prompt", lang)
    await message.answer(f"{prompt_text}\n\n{hitalic(skip_info)}\n{hitalic(cancel_info)}", parse_mode="HTML")


@router.message(StateFilter(AdminProductStates.PRODUCT_AWAIT_IMAGE_URL), F.text)
async def fsm_admin_prod_image_url_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    if message.text.lower() == "/cancel":
        mock_callback = types.CallbackQuery(id=str(message.message_id)+"_cancel", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
        return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    image_url_input = sanitize_input(message.text)
    image_url = image_url_input if image_url_input != "-" else None
    
    # Basic URL validation could be added here if desired, e.g. checking for http/https
    # For now, any non-empty string (or None if skipped) is accepted.

    current_product_data = (await state.get_data()).get("product_data", {})
    current_product_data["image_url"] = image_url
    await state.update_data(product_data=current_product_data)

    # Transition to localization
    await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_LANG_CODE)
    # Call the helper that asks for localization language
    # We need a message or callback object for this helper. Let's use the current message.
    await _admin_prod_create_ask_localization_lang(message, state, user_data)


# --- Localization Loop Handlers for Product Creation ---

async def _admin_prod_create_ask_localization_lang(
    event: Union[types.Message, types.CallbackQuery], 
    state: FSMContext, 
    user_data: Dict[str, Any]
):
    lang = user_data.get("language", "en") # Admin's language
    state_data = await state.get_data()
    product_localizations_temp = state_data.get("product_localizations_temp", [])
    existing_lang_codes = [loc['language_code'] for loc in product_localizations_temp]

    # Check if all supported languages are already localized
    # (Assuming ALL_TEXTS['language_name_en'] contains all supported bot languages)
    # This import might be better at the top of the file.
    from app.localization.locales import TEXTS as ALL_LANG_TEXTS 
    all_supported_langs = list(ALL_LANG_TEXTS.get("language_name_en", {}).keys())
    
    available_langs_for_new_loc = [lc for lc in all_supported_langs if lc not in existing_lang_codes and lc is not None]

    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    
    if not available_langs_for_new_loc and not product_localizations_temp:
        # This case should ideally not be reached if the first localization is enforced.
        # For now, if it happens, prompt for the admin's current language as the first localization lang.
        # Or, could force a specific default like 'en'.
        # This ensures at least one localization is attempted.
        first_loc_lang_to_try = lang 
        if first_loc_lang_to_try in existing_lang_codes: # Should not happen if product_localizations_temp is empty
            first_loc_lang_to_try = 'en' if 'en' not in existing_lang_codes else (all_supported_langs[0] if all_supported_langs else 'en')

        if first_loc_lang_to_try: # Ensure there's a lang to try
             await state.update_data(current_localization_lang=first_loc_lang_to_try)
             await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_NAME)
             prompt_text = get_text("admin_prod_enter_loc_name_forced_first", lang, lang_name=get_text(f"language_name_{first_loc_lang_to_try}", lang))
             cancel_info = get_text("cancel_prompt", lang)
             await target_message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
             if isinstance(event, types.CallbackQuery): await event.answer()
             return
        else: # No supported languages at all (config issue)
            await target_message.answer(get_text("admin_prod_error_no_languages_configured", lang), reply_markup=types.ReplyKeyboardRemove())
            # Potentially cancel flow or go back to product menu
            mock_callback = types.CallbackQuery(id=str(event.id)+"_err_no_lang", from_user=event.from_user, chat_instance=str(target_message.chat.id), message=target_message, data="admin_prod_add_cancel_to_menu")
            await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)
            if isinstance(event, types.CallbackQuery): await event.answer()
            return


    await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_LANG_CODE)
    
    # Use the existing keyboard function and add "Done" button dynamically
    # The product_id argument in create_admin_select_lang_for_localization_keyboard is not relevant for new product creation.
    # We can pass a dummy one or modify the keyboard function if it's problematic. For now, assume it handles it or pass 0.
    builder = InlineKeyboardBuilder.from_markup(
        create_admin_select_lang_for_localization_keyboard(
            product_id=0, # Dummy product_id for new product
            action_prefix="admin_prod_create_select_loc_lang", 
            language=lang, 
            existing_lang_codes=existing_lang_codes
        )
    )

    if product_localizations_temp: # If at least one localization has been added
        builder.row(InlineKeyboardButton(
            text=get_text("admin_prod_done_localizations", lang), 
            callback_data="admin_prod_create_confirm_details"
        ))
    
    prompt_text_key = "admin_prod_select_loc_lang"
    if not available_langs_for_new_loc and product_localizations_temp: # All langs done, only "Done" makes sense
        prompt_text_key = "admin_prod_all_langs_localized_proceed"
    elif not product_localizations_temp: # First localization being added
        prompt_text_key = "admin_prod_select_first_loc_lang"


    final_prompt_text = get_text(prompt_text_key, lang)
    
    # If message is from a text input, send new message. If callback, edit.
    if isinstance(event, types.Message):
        await event.answer(final_prompt_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    elif isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(final_prompt_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception: # If edit fails, send as new message
             await event.message.answer(final_prompt_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await event.answer()


@router.callback_query(F.data.startswith("admin_prod_create_select_loc_lang:"), StateFilter(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_LANG_CODE))
async def cq_admin_prod_create_select_loc_lang(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en") # Admin's language
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    selected_loc_lang = callback.data.split(":")[2]
    
    # Validate selected_loc_lang (e.g. ensure it's in supported languages) - though keyboard should only show valid ones
    from app.localization.locales import TEXTS as ALL_LANG_TEXTS
    if selected_loc_lang not in ALL_LANG_TEXTS.get("language_name_en", {}):
        await callback.answer(get_text("error_occurred", lang) + " Invalid language selected.", show_alert=True)
        # Re-ask for language
        return await _admin_prod_create_ask_localization_lang(callback, state, user_data)

    await state.update_data(current_localization_lang=selected_loc_lang)
    await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_NAME)
    
    lang_display_name = get_text(f"language_name_{selected_loc_lang}", lang) # Get display name in admin's language
    prompt_text = get_text("admin_prod_enter_loc_name", lang, lang_name=lang_display_name)
    cancel_info = get_text("cancel_prompt", lang)

    try:
        await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=None)
    except Exception:
        await callback.message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await callback.answer()


@router.message(StateFilter(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_NAME), F.text)
async def fsm_admin_prod_loc_name_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(message.from_user.id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    state_data = await state.get_data()
    product_id_for_edit_context = state_data.get("current_edit_product_id")
    # Determine active language code (either being edited or being added)
    active_loc_lang_code = state_data.get("editing_loc_lang_code") or state_data.get("current_localization_lang")

    if message.text.lower() == "/cancel":
        if product_id_for_edit_context: # If editing an existing product's localization
            await message.answer(get_text("admin_action_cancelled", lang))
            temp_msg = await message.answer(get_text("loading_text", lang), reply_markup=types.ReplyKeyboardRemove())
            mock_cb = types.CallbackQuery(id=str(message.message_id)+"_cancel_loc_edit", from_user=message.from_user, chat_instance=str(message.chat.id), message=temp_msg, data=f"admin_prod_edit_locs_menu:{product_id_for_edit_context}")
            return await cq_admin_prod_edit_locs_menu(mock_cb, state, user_data)
        else: # Product creation flow
            mock_callback = types.CallbackQuery(id=str(message.message_id)+"_cancel_loc_create", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
            return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    loc_name = sanitize_input(message.text)
    if not loc_name:
        lang_display_name = get_text(f"language_name_{active_loc_lang_code}", lang, default=active_loc_lang_code.upper() if active_loc_lang_code else "the language")
        await message.answer(get_text("admin_prod_loc_name_empty", lang, lang_name=lang_display_name))
        prompt_text = get_text("admin_prod_enter_loc_name", lang, lang_name=lang_display_name)
        cancel_info_key = "cancel_prompt_short_to_loc_menu" if product_id_for_edit_context else "cancel_prompt"
        cancel_text = get_text(cancel_info_key, lang, command="/cancel", product_id=product_id_for_edit_context)
        await message.answer(f"{prompt_text}\n\n{hitalic(cancel_text)}", parse_mode="HTML")
        return

    await state.update_data(current_localization_name_temp=loc_name) # Store temporarily
    await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_DESCRIPTION)
    
    lang_display_name = get_text(f"language_name_{active_loc_lang_code}", lang, default=active_loc_lang_code.upper() if active_loc_lang_code else "the language")
    prompt_text = get_text("admin_prod_enter_loc_desc", lang, lang_name=lang_display_name)
    skip_info = get_text("admin_prod_skip_instruction_generic", lang)
    cancel_info_key = "cancel_prompt_short_to_loc_menu" if product_id_for_edit_context else "cancel_prompt"
    cancel_text = get_text(cancel_info_key, lang, command="/cancel", product_id=product_id_for_edit_context)
    await message.answer(f"{prompt_text}\n\n{hitalic(skip_info)}\n{hitalic(cancel_text)}", parse_mode="HTML")


@router.message(StateFilter(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_DESCRIPTION), F.text)
async def fsm_admin_prod_loc_desc_received(message: types.Message, user_data: Dict[str, Any], state: FSMContext):
    lang = user_data.get("language", "en")
    admin_id = message.from_user.id
    user_service = UserService()
    product_service = ProductService() # For saving localization
    if not await is_admin_user_check(admin_id, user_service):
        return await message.answer(get_text("admin_access_denied", lang))

    state_data = await state.get_data()
    product_id_for_edit_context = state_data.get("current_edit_product_id")
    active_loc_lang_code = state_data.get("editing_loc_lang_code") or state_data.get("current_localization_lang")
    current_loc_name = state_data.get("current_localization_name_temp") # Use temp name

    if message.text.lower() == "/cancel":
        if product_id_for_edit_context:
            await message.answer(get_text("admin_action_cancelled", lang))
            temp_msg = await message.answer(get_text("loading_text", lang), reply_markup=types.ReplyKeyboardRemove())
            mock_cb = types.CallbackQuery(id=str(message.message_id)+"_cancel_loc_edit_desc", from_user=message.from_user, chat_instance=str(message.chat.id), message=temp_msg, data=f"admin_prod_edit_locs_menu:{product_id_for_edit_context}")
            return await cq_admin_prod_edit_locs_menu(mock_cb, state, user_data)
        else:
            mock_callback = types.CallbackQuery(id=str(message.message_id)+"_cancel_loc_create_desc", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
            return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    loc_desc_input = sanitize_input(message.text)
    loc_desc = loc_desc_input if loc_desc_input != "-" else None

    if not active_loc_lang_code or not current_loc_name:
        await message.answer(get_text("admin_action_failed_no_context", lang))
        # Determine correct cancel/fallback
        if product_id_for_edit_context:
            temp_msg = await message.answer(get_text("loading_text", lang),reply_markup=types.ReplyKeyboardRemove())
            mock_cb = types.CallbackQuery(id=str(message.message_id)+"_ctx_lost_loc_edit", from_user=message.from_user, chat_instance=str(message.chat.id), message=temp_msg, data=f"admin_prod_edit_locs_menu:{product_id_for_edit_context}")
            return await cq_admin_prod_edit_locs_menu(mock_cb, state, user_data)
        else:
            mock_callback = types.CallbackQuery(id=str(message.message_id)+"_ctx_lost_loc_create", from_user=message.from_user, chat_instance=str(message.chat.id), message=message, data="admin_prod_add_cancel_to_menu")
            return await cq_admin_prod_add_cancel_to_menu(mock_callback, state, user_data)

    if product_id_for_edit_context: # Editing/Adding localization for an EXISTING product
        success, msg_key = await product_service.add_or_update_product_localization_service(
            admin_id=admin_id, product_id=product_id_for_edit_context,
            loc_lang_code=active_loc_lang_code, name=current_loc_name, description=loc_desc, lang=lang
        )
        await message.answer(get_text(msg_key, lang, lang_name=get_text(f"language_name_{active_loc_lang_code}",lang, default=active_loc_lang_code.upper())))
        
        # Clear temporary localization data and editing flags
        await state.update_data(current_localization_lang=None, editing_loc_lang_code=None, current_localization_name_temp=None)
        
        # Go back to the localization menu for the current product
        temp_msg_for_loc_menu = await message.answer(get_text("loading_text", lang),reply_markup=types.ReplyKeyboardRemove())
        mock_callback_to_loc_menu = types.CallbackQuery(
            id=str(message.message_id) + "_after_loc_save", from_user=message.from_user,
            chat_instance=str(message.chat.id), message=temp_msg_for_loc_menu, data=f"admin_prod_edit_locs_menu:{product_id_for_edit_context}"
        )
        await cq_admin_prod_edit_locs_menu(mock_callback_to_loc_menu, state, user_data)

    else: # Part of NEW product creation flow
        product_localizations_temp = state_data.get("product_localizations_temp", [])
        # Update if lang_code already in temp list (e.g. user went back and re-added for same lang)
        found_idx = -1
        for i, loc in enumerate(product_localizations_temp):
            if loc["language_code"] == active_loc_lang_code:
                found_idx = i
                break
        if found_idx != -1:
            product_localizations_temp[found_idx] = {"language_code": active_loc_lang_code, "name": current_loc_name, "description": loc_desc}
        else:
            product_localizations_temp.append({"language_code": active_loc_lang_code, "name": current_loc_name, "description": loc_desc})
        
        await state.update_data(product_localizations_temp=product_localizations_temp)
        await state.update_data(current_localization_lang=None, current_localization_name_temp=None) # Clear single loc context
        
        lang_display_name = get_text(f"language_name_{active_loc_lang_code}", lang, default=active_loc_lang_code.upper())
        await message.answer(get_text("admin_prod_loc_added_ask_more", lang, lang_name=lang_display_name))
        await _admin_prod_create_ask_localization_lang(message, state, user_data) # Loop for new product


# --- Product Localization Edit/Add Handlers (for existing product) ---

@router.callback_query(F.data.startswith("admin_prod_edit_locs_menu:"), StateFilter("*")) # Accessible from product edit options
async def cq_admin_prod_edit_locs_menu(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        product_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID.", show_alert=True)
        # Go back to main product menu if ID is bad
        prod_menu_text = get_text("admin_product_management_title", lang)
        prod_menu_kb = create_admin_product_management_menu_keyboard(lang)
        await callback.message.edit_text(prod_menu_text, reply_markup=prod_menu_kb)
        return

    product_details = await product_service.get_product_details_for_admin(product_id, lang)
    if not product_details:
        await callback.answer(get_text("admin_product_not_found", lang), show_alert=True)
        # Go back to product selection for editing
        return await cq_admin_prod_edit_select(callback, state, user_data)


    await state.set_state(AdminProductStates.PRODUCT_MANAGE_LOCALIZATIONS)
    await state.update_data(
        current_edit_product_id=product_id, 
        current_edit_product_name=product_details.get("sku", str(product_id)) # Basic name for context
    )
    
    # create_admin_localization_actions_keyboard expects product_id, list of current localizations, and admin lang
    # The list of localizations should be part of product_details
    existing_localizations = product_details.get("localizations", [])
    
    keyboard = create_admin_localization_actions_keyboard(product_id, existing_localizations, lang)
    title = get_text("admin_prod_edit_locs_menu_title", lang, product_name=hbold(product_details.get("sku", str(product_id))))

    try:
        await callback.message.edit_text(title, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(title, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_edit_loc_select:"), StateFilter(AdminProductStates.PRODUCT_MANAGE_LOCALIZATIONS))
async def cq_admin_prod_edit_loc_select(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    """Handles selection of an existing localization to edit its name/description."""
    lang = user_data.get("language", "en") # Admin's language
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(":")
    if len(parts) != 3: # prefix:product_id:loc_lang_code
        await callback.answer(get_text("error_occurred", lang) + " Invalid localization selection.", show_alert=True)
        return

    product_id_str, loc_lang_code_to_edit = parts[1], parts[2]
    try:
        product_id = int(product_id_str)
    except ValueError:
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID for loc edit.", show_alert=True)
        return # Or navigate back

    await state.update_data(
        current_edit_product_id=product_id, # Already should be there, but good to confirm
        editing_loc_lang_code=loc_lang_code_to_edit, # Specific for editing existing
        current_localization_lang=None # Clear if adding new
    )
    await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_NAME)
    
    # Get display name for the language being edited (in admin's current language)
    lang_display_name = get_text(f"language_name_{loc_lang_code_to_edit}", lang, default=loc_lang_code_to_edit.upper())
    prompt_text = get_text("admin_prod_edit_loc_enter_name", lang, lang_name=lang_display_name)
    cancel_info = get_text("cancel_prompt_short", lang, command="/cancel") # Cancel goes to loc menu

    try:
        await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=None)
    except Exception:
        await callback.message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_add_loc_start:"), StateFilter(AdminProductStates.PRODUCT_MANAGE_LOCALIZATIONS))
async def cq_admin_prod_add_loc_start(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    """Handles 'Add Localization' button for an existing product."""
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        product_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID for adding loc.", show_alert=True)
        return

    # Fetch existing localizations to exclude them from selection
    product_details = await product_service.get_product_details_for_admin(product_id, lang)
    if not product_details: # Should not happen if user is in this menu
        await callback.answer(get_text("admin_product_not_found", lang), show_alert=True)
        return
    
    existing_lang_codes = [loc['lang_code'] for loc in product_details.get("localizations", [])]

    await state.update_data(
        current_edit_product_id=product_id, # Keep product context
        editing_loc_lang_code=None, # Clear if editing existing
        current_localization_lang=None # Will be set by next step
    )
    await state.set_state(AdminProductStates.PRODUCT_SELECT_NEW_LOCALIZATION_LANG)

    keyboard = create_admin_select_lang_for_localization_keyboard(
        product_id=product_id,
        action_prefix="admin_prod_edit_add_new_loc_lang", # Specific callback for this flow
        language=lang,
        existing_lang_codes=existing_lang_codes
    )
    prompt_text = get_text("admin_prod_add_loc_select_lang", lang)
    
    # Check if any languages are available to add
    from app.localization.locales import TEXTS as ALL_LANG_TEXTS 
    all_supported_langs = list(ALL_LANG_TEXTS.get("language_name_en", {}).keys())
    available_to_add = [lc for lc in all_supported_langs if lc not in existing_lang_codes and lc is not None]

    if not available_to_add:
        prompt_text = get_text("admin_prod_all_langs_already_localized", lang)
        # Keyboard will be just a cancel/back button from create_admin_select_lang_for_localization_keyboard
        # if no languages are available.

    try:
        await callback.message.edit_text(prompt_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(prompt_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_edit_add_new_loc_lang:"), StateFilter(AdminProductStates.PRODUCT_SELECT_NEW_LOCALIZATION_LANG))
async def cq_admin_prod_edit_add_new_loc_lang(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    """Handles selection of a new language to add localization for an existing product."""
    lang = user_data.get("language", "en") # Admin's language
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    parts = callback.data.split(":")
    if len(parts) != 3: # prefix:product_id:new_loc_lang
        await callback.answer(get_text("error_occurred", lang) + " Invalid lang selection for new loc.", show_alert=True)
        return

    product_id_str, new_loc_lang_code = parts[1], parts[2]
    try:
        product_id = int(product_id_str)
    except ValueError: # Should not happen with keyboard
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID for new loc lang.", show_alert=True)
        return

    await state.update_data(
        current_edit_product_id=product_id, 
        current_localization_lang=new_loc_lang_code, # This is for a NEW localization being added
        editing_loc_lang_code=None # Clear this to signify it's not editing an existing one
    )
    await state.set_state(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_NAME)
    
    lang_display_name = get_text(f"language_name_{new_loc_lang_code}", lang)
    prompt_text = get_text("admin_prod_enter_loc_name", lang, lang_name=lang_display_name) # Re-use existing key
    cancel_info = get_text("cancel_prompt_short", lang, command="/cancel") # Cancel goes to loc menu

    try:
        await callback.message.edit_text(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=None)
    except Exception:
        await callback.message.answer(f"{prompt_text}\n\n{hitalic(cancel_info)}", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await callback.answer()

# fsm_admin_prod_loc_name_received and fsm_admin_prod_loc_desc_received need to be context-aware
# (create vs edit product, and add new loc vs edit existing loc for a product)
# The main change will be the navigation at the end:
# - If creating product -> _admin_prod_create_ask_localization_lang
# - If editing product's localizations -> cq_admin_prod_edit_locs_menu (mocked callback)

# The existing fsm_admin_prod_loc_name_received and fsm_admin_prod_loc_desc_received
# already use state_data.get("current_localization_lang") for the language code,
# which is set correctly by cq_admin_prod_edit_loc_select (as editing_loc_lang_code then used)
# or by cq_admin_prod_edit_add_new_loc_lang (as current_localization_lang).
# The main difference is the "cancel" and "after save" navigation.
# We need to ensure /cancel in these states, when editing an existing product's localization,
# goes back to the localization menu for that product (cq_admin_prod_edit_locs_menu).

# The existing `fsm_admin_prod_loc_desc_received` calls `_admin_prod_create_ask_localization_lang`
# This needs to be conditional. If `editing_loc_lang_code` is in state, it means we are editing
# an existing product's localization, so after saving, we should go back to `cq_admin_prod_edit_locs_menu`.

# This will require modifying fsm_admin_prod_loc_desc_received and potentially fsm_admin_prod_loc_name_received
# for their /cancel behavior when in the context of editing an existing product.
# For now, I will assume the existing structure of these two handlers will be adapted or
# new specific handlers will be created if the logic becomes too complex.
# The service method `add_or_update_product_localization_service` is fine.


# --- Product Deletion Handlers ---

@router.callback_query(F.data.startswith("admin_prod_delete_confirm:"), StateFilter("*")) # Can be called from product view
async def cq_admin_prod_delete_confirm(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        product_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID for delete confirmation.", show_alert=True)
        # Go back to product list if ID is bad
        return await _send_paginated_products_list(callback, state, user_data, page=0)

    # Fetch product details to get its name for the confirmation message
    product_details = await product_service.get_product_details_for_admin(product_id, lang)
    if not product_details:
        await callback.answer(get_text("admin_product_not_found", lang), show_alert=True)
        return await _send_paginated_products_list(callback, state, user_data, page=0)

    # Determine a primary name for confirmation
    product_name_display = product_details.get("sku", str(product_id)) # Default
    if product_details.get("localizations"):
        name_found = False
        for loc in product_details["localizations"]:
            if loc['lang_code'] == lang:
                product_name_display = loc['name']
                name_found = True
                break
        if not name_found: # Fallback to English or first if admin lang not found
            for loc_item in product_details["localizations"]: # Renamed loc to loc_item to avoid conflict
                if loc_item['lang_code'] == 'en':
                    product_name_display = loc_item['name']
                    name_found = True
                    break
            if not name_found and product_details["localizations"]: # Check if localizations list is not empty
                 product_name_display = product_details["localizations"][0]['name']


    await state.set_state(AdminProductStates.PRODUCT_CONFIRM_DELETE)
    await state.update_data(
        product_to_delete_id=product_id,
        product_to_delete_name=product_name_display 
    )

    confirmation_text = get_text("admin_prod_confirm_delete_prompt", lang, product_name=hbold(product_name_display), product_id=product_id)
    keyboard = create_confirmation_keyboard(
        language=lang,
        yes_callback=f"admin_prod_execute_delete:{product_id}",
        no_callback=f"admin_prod_view:{product_id}" # Back to view details of this product
    )
    
    try:
        await callback.message.edit_text(confirmation_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception: # If message too long or other error
        await callback.message.answer(confirmation_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_execute_delete:"), StateFilter(AdminProductStates.PRODUCT_CONFIRM_DELETE))
async def cq_admin_prod_execute_delete(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    admin_id = callback.from_user.id
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(admin_id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    product_id_from_state = state_data.get("product_to_delete_id")
    product_name_from_state = state_data.get("product_to_delete_name", f"ID {product_id_from_state}")

    try:
        product_id_from_cb = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID in delete execution.", show_alert=True)
        return await _send_paginated_products_list(callback, state, user_data, page=0) # Fallback to list

    if product_id_from_state != product_id_from_cb:
        logger.warning(f"Product ID mismatch during delete execution. State: {product_id_from_state}, Callback: {product_id_from_cb}. Using callback ID.")
        # Re-fetch name for accuracy if this happens, though product_service.delete_product_by_admin also fetches name
        temp_details_for_name = await product_service.get_product_details_for_admin(product_id_from_cb, lang)
        if temp_details_for_name:
            product_name_from_state = temp_details_for_name.get("sku", str(product_id_from_cb)) # Update name based on CB ID
            if temp_details_for_name.get("localizations"):
                name_found = False
                for loc in temp_details_for_name["localizations"]:
                    if loc['lang_code'] == lang: product_name_from_state = loc['name']; name_found = True; break
                if not name_found:
                    for loc in temp_details_for_name["localizations"]:
                        if loc['lang_code'] == 'en': product_name_from_state = loc['name']; name_found = True; break
                    if not name_found and temp_details_for_name["localizations"]: product_name_from_state = temp_details_for_name["localizations"][0]['name']


    success, message_key, deleted_product_name = await product_service.delete_product_by_admin(
        admin_id=admin_id,
        product_id=product_id_from_cb, 
        lang=lang
    )
    
    display_name_for_message = deleted_product_name or product_name_from_state # Prefer name from service response

    final_message = get_text(message_key, lang, product_name=hbold(display_name_for_message), product_id=product_id_from_cb)
    await callback.answer(final_message, show_alert=True) 

    await state.clear() 
    
    # Navigate back to product list (page 0)
    # Need to ensure the target message for _send_paginated_products_list can be edited
    # If original message was from a button that opened a new message for confirmation, this might be tricky.
    # For now, assume callback.message is the one to edit.
    await _send_paginated_products_list(callback, state, user_data, page=0)


 # --- Product List and View Details Handlers ---

@router.callback_query(F.data.startswith("admin_prod_delete_confirm:"), StateFilter("*")) # Can be called from product view
async def cq_admin_prod_delete_confirm(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        product_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID for delete confirmation.", show_alert=True)
        # Go back to product list if ID is bad
        return await _send_paginated_products_list(callback, state, user_data, page=0)

    # Fetch product details to get its name for the confirmation message
    product_details = await product_service.get_product_details_for_admin(product_id, lang)
    if not product_details:
        await callback.answer(get_text("admin_product_not_found", lang), show_alert=True)
        return await _send_paginated_products_list(callback, state, user_data, page=0)

    # Determine a primary name for confirmation
    product_name_display = product_details.get("sku", str(product_id)) # Default
    if product_details.get("localizations"):
        name_found = False
        for loc in product_details["localizations"]:
            if loc['lang_code'] == lang:
                product_name_display = loc['name']
                name_found = True
                break
        if not name_found: # Fallback to English or first if admin lang not found
            for loc in product_details["localizations"]:
                if loc['lang_code'] == 'en':
                    product_name_display = loc['name']
                    name_found = True
                    break
            if not name_found and product_details["localizations"]:
                 product_name_display = product_details["localizations"][0]['name']


    await state.set_state(AdminProductStates.PRODUCT_CONFIRM_DELETE)
    await state.update_data(
        product_to_delete_id=product_id,
        product_to_delete_name=product_name_display 
    )

    confirmation_text = get_text("admin_prod_confirm_delete_prompt", lang, product_name=hbold(product_name_display), product_id=product_id)
    keyboard = create_confirmation_keyboard(
        language=lang,
        yes_callback=f"admin_prod_execute_delete:{product_id}",
        no_callback=f"admin_prod_view:{product_id}" # Back to view details of this product
    )
    
    try:
        await callback.message.edit_text(confirmation_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception: # If message too long or other error
        await callback.message.answer(confirmation_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_execute_delete:"), StateFilter(AdminProductStates.PRODUCT_CONFIRM_DELETE))
async def cq_admin_prod_execute_delete(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    admin_id = callback.from_user.id
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(admin_id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    product_id_from_state = state_data.get("product_to_delete_id")
    product_name_from_state = state_data.get("product_to_delete_name", f"ID {product_id_from_state}")

    try:
        product_id_from_cb = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang) + " Invalid product ID in delete execution.", show_alert=True)
        return await _send_paginated_products_list(callback, state, user_data, page=0) # Fallback to list

    if product_id_from_state != product_id_from_cb:
        logger.warning(f"Product ID mismatch during delete execution. State: {product_id_from_state}, Callback: {product_id_from_cb}. Using callback ID.")
        # Potentially re-fetch name if relying on it and state might be stale, but service call will use callback ID.
        # For now, product_name_from_state will be used for messages.

    success, message_key, deleted_product_name = await product_service.delete_product_by_admin(
        admin_id=admin_id,
        product_id=product_id_from_cb, # Use ID from callback as primary
        lang=lang
    )
    
    # Use the name returned by the service if available (it tries to fetch it), otherwise name from state.
    display_name = deleted_product_name or product_name_from_state

    final_message = get_text(message_key, lang, product_name=hbold(display_name), product_id=product_id_from_cb)
    await callback.answer(final_message, show_alert=True) # Show as alert

    await state.clear() # Clear FSM state
    
    # Navigate back to product list (page 0)
    await _send_paginated_products_list(callback, state, user_data, page=0)


# --- Product List and View Details Handlers ---

async def _send_paginated_products_list(
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

    products_on_page_data, total_products = await product_service.get_products_for_admin_list(
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        lang=lang
    )

    title = get_text("admin_product_list_title", lang)

    if not products_on_page_data and page == 0:
        empty_text = title + "\n\n" + get_text("admin_no_products_found", lang)
        kb = InlineKeyboardBuilder().row(create_back_button("back_to_product_management", lang, "admin_products_menu")).as_markup()
        
        target_message = event.message if isinstance(event, types.CallbackQuery) else event
        if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
             await target_message.edit_text(empty_text, reply_markup=kb)
        else:
             await target_message.answer(empty_text, reply_markup=kb)
        if isinstance(event, types.CallbackQuery): await event.answer()
        return

    # The 'name' field from get_products_for_admin_list is already formatted for display.
    # It includes name, then SKU and cost, e.g., "Product A (SKU: 123) - 10.99 USD"
    # So, item_text_key="name" should work directly.
    # Define base_callback_data and item_callback_prefix, or allow override if needed.
    current_base_callback_data = "admin_prod_list_page" # Default for general product list
    current_item_callback_prefix = "admin_prod_view" # Default for viewing product

    # Example of how overrides might be used if this function was more generic:
    # base_callback_data_to_use = base_callback_data_override or current_base_callback_data
    # item_callback_prefix_to_use = item_callback_prefix_override or current_item_callback_prefix
    # back_callback_key_to_use = back_callback_key_override or "back_to_product_management"
    # back_callback_data_to_use = back_callback_data_override or "admin_products_menu"


    keyboard = create_paginated_keyboard(
        items=products_on_page_data,
        page=page,
        items_per_page=ITEMS_PER_PAGE_ADMIN,
        base_callback_data=current_base_callback_data, # Use defined or overridden
        item_callback_prefix=current_item_callback_prefix, # Use defined or overridden
        language=lang,
        back_callback_key="back_to_product_management", # Default or allow override
        back_callback_data="admin_products_menu", # Default or allow override
        total_items_override=total_products,
        item_text_key="name", 
        item_id_key="id"
    )
    
    target_message = event.message if isinstance(event, types.CallbackQuery) else event
    if hasattr(target_message, "edit_text") and isinstance(event, types.CallbackQuery):
        await target_message.edit_text(title, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target_message.answer(title, reply_markup=keyboard, parse_mode="HTML")
        
    if isinstance(event, types.CallbackQuery): await event.answer()

@router.callback_query(F.data == "admin_prod_list:0", StateFilter("*")) # Entry point from product menu
async def cq_admin_prod_list(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    
    # Clear any product-specific state if coming from another product operation
    await state.clear() # Or selectively clear if needed
    await _send_paginated_products_list(callback, state, user_data, page=0)

@router.callback_query(F.data.startswith("admin_prod_list_page:"), StateFilter("*")) # Pagination
async def cq_admin_prod_list_paginate(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 0
    await _send_paginated_products_list(callback, state, user_data, page=page)


def _format_product_details_for_admin_view(details: Dict[str, Any], lang: str) -> str:
    """Helper to format product details for admin view message."""
    
    # Determine a primary name for the title, fallback to SKU or ID
    primary_name = details.get("sku", str(details['id']))
    if details.get("localizations"):
        for loc in details["localizations"]:
            if loc['lang_code'] == lang:
                primary_name = loc['name']
                break
        if primary_name == details.get("sku", str(details['id'])): # if lang not found, try 'en'
             for loc in details["localizations"]:
                if loc['lang_code'] == 'en':
                    primary_name = loc['name']
                    break
    
    view_text = get_text("admin_product_view_title", lang, product_name=hbold(primary_name)) + "\n\n"
    
    view_text += f"{hbold(get_text('admin_prod_detail_id', lang))}: {hcode(details['id'])}\n"
    view_text += f"{hbold(get_text('admin_prod_detail_sku', lang))}: {hcode(details['sku'])}\n"
    view_text += f"{hbold(get_text('admin_prod_detail_manufacturer', lang))}: {hcode(details['manufacturer_name'])}\n"
    view_text += f"{hbold(get_text('admin_prod_detail_category', lang))}: {hcode(details['category_name'])}\n"
    view_text += f"{hbold(get_text('admin_prod_detail_cost', lang))}: {details['cost']}\n" # Already formatted by service
    view_text += f"{hbold(get_text('admin_prod_detail_variation', lang))}: {hcode(details['variation'])}\n"
    
    if details.get('image_url'):
        view_text += f"{hbold(get_text('admin_prod_detail_image_url', lang))}: {hlink('View Image', details['image_url'])}\n"
    else:
        view_text += f"{hbold(get_text('admin_prod_detail_image_url', lang))}: {get_text('not_set', lang)}\n"

    view_text += f"\n{hbold(get_text('admin_prod_detail_localizations_header', lang))}:\n"
    if details.get("localizations"):
        for loc in details["localizations"]:
            lang_code_display = get_text(f"language_name_{loc['lang_code']}", lang, default=loc['lang_code'].upper())
            desc_display = hitalic(loc.get('description')) if loc.get('description') != get_text('not_set', lang) else get_text('not_set', lang)
            view_text += f"  <b>{lang_code_display}:</b>\n"
            view_text += f"    <i>{get_text('name_label', lang)}:</i> {hbold(loc['name'])}\n"
            view_text += f"    <i>{get_text('description_label', lang)}:</i> {desc_display}\n"
    else:
        view_text += f"  {get_text('admin_prod_no_localizations_added_summary', lang)}\n" # Re-use existing key

    view_text += f"\n{hbold(get_text('admin_prod_detail_stock_header', lang))}:\n"
    if details.get("stock_summary"):
        for stock_info in details["stock_summary"]:
            view_text += f"  - {hcode(stock_info['location_name'])}: {stock_info['quantity']} {get_text('units_short', lang)}\n"
    else:
        view_text += f"  {get_text('admin_prod_no_stock_data', lang)}\n"
        
    return view_text

@router.callback_query(F.data.startswith("admin_prod_view:"), StateFilter("*"))
async def cq_admin_prod_view(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    try:
        product_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(get_text("error_occurred", lang), show_alert=True)
        return await _send_paginated_products_list(callback, state, user_data, page=0) # Go back to list

    product_details_data = await product_service.get_product_details_for_admin(product_id, lang)

    if not product_details_data:
        await callback.answer(get_text("admin_product_not_found", lang), show_alert=True)
        return await _send_paginated_products_list(callback, state, user_data, page=0) # Go back to list

    # Store product_id in state in case it's needed by edit/delete from this view
    await state.update_data(current_product_id_admin_view=product_id) 
    # Clear other product states if any, or set a specific state for viewing product
    # For now, not setting a specific state for just viewing, actions will set their own.

    formatted_text = _format_product_details_for_admin_view(product_details_data, lang)
    
    from app.keyboards.inline import create_admin_product_view_actions_keyboard
    keyboard = create_admin_product_view_actions_keyboard(product_id, lang)

    try:
        await callback.message.edit_text(formatted_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e: # Handle message too long or other errors
        logger.error(f"Error editing message for product view {product_id}: {e}")
        # Send as new message if edit fails
        await callback.message.answer(formatted_text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()


# --- Product Creation Confirmation and Execution ---

def _format_product_confirmation_details(product_data: Dict[str, Any], localizations: List[Dict[str, str]], lang: str) -> str:
    """Helper to format product details for confirmation message."""
    details_text = get_text("admin_prod_confirm_add_details_title", lang) + "\n\n"
    
    details_text += f"{hbold(get_text('product_field_name_manufacturer_id', lang))}: {product_data.get('manufacturer_name', product_data.get('manufacturer_id', get_text('not_set', lang)))}\n"
    details_text += f"{hbold(get_text('product_field_name_category_id', lang))}: {product_data.get('category_name', product_data.get('category_id', get_text('not_set', lang)))}\n"
    details_text += f"{hbold(get_text('product_field_name_cost', lang))}: {format_price(product_data.get('cost', 0), lang)}\n" # Assuming format_price can handle Decimal
    details_text += f"{hbold(get_text('product_field_name_sku', lang))}: {hcode(product_data.get('sku')) if product_data.get('sku') else get_text('not_set', lang)}\n"
    details_text += f"{hbold(get_text('product_field_name_variation', lang))}: {hcode(product_data.get('variation')) if product_data.get('variation') else get_text('not_set', lang)}\n"
    details_text += f"{hbold(get_text('product_field_name_image_url', lang))}: {hlink('Link', product_data['image_url']) if product_data.get('image_url') else get_text('not_set', lang)}\n"
    
    details_text += f"\n{hbold(get_text('product_field_name_localizations', lang))}:\n"
    if localizations:
        for loc in localizations:
            lang_code_display = get_text(f"language_name_{loc['language_code']}", lang, default=loc['language_code'].upper())
            desc_display = hitalic(loc.get('description')) if loc.get('description') else get_text('not_set', lang)
            details_text += f"  - {lang_code_display}:\n"
            details_text += f"    {get_text('name_label', lang, default='Name')}: {hbold(loc['name'])}\n"
            details_text += f"    {get_text('description_label', lang, default='Description')}: {desc_display}\n"
    else:
        details_text += f"  {get_text('admin_prod_no_localizations_added_summary', lang)}\n"
        
    return details_text

@router.callback_query(F.data == "admin_prod_create_confirm_details", StateFilter(AdminProductStates.PRODUCT_AWAIT_LOCALIZATION_LANG_CODE))
async def cq_admin_prod_create_confirm_details(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    user_service = UserService()
    if not await is_admin_user_check(callback.from_user.id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    product_main_data = state_data.get("product_data", {})
    product_localizations = state_data.get("product_localizations_temp", [])

    if not product_main_data.get("manufacturer_id") or not product_main_data.get("cost") or not product_localizations:
        await callback.answer(get_text("admin_prod_error_incomplete_data_for_confirmation", lang), show_alert=True)
        # Send back to product menu as something went wrong
        mock_cb_for_cancel = types.CallbackQuery(id=callback.id + "_incomplete", from_user=callback.from_user, chat_instance=callback.message.chat.id, message=callback.message, data="admin_prod_add_cancel_to_menu")
        return await cq_admin_prod_add_cancel_to_menu(mock_cb_for_cancel, state, user_data)

    await state.set_state(AdminProductStates.PRODUCT_CONFIRM_ADD)
    
    summary_text = _format_product_confirmation_details(product_main_data, product_localizations, lang)
    prompt_text = get_text("admin_prod_confirm_add_details_prompt", lang)
    
    keyboard = create_confirmation_keyboard(
        language=lang,
        yes_callback="admin_prod_create_execute_add",
        no_callback="admin_prod_add_cancel_to_menu", # Cancels and returns to product menu
        yes_text_key="confirm_and_add_product",
        no_text_key="cancel_add_product_short"
    )
    
    full_message = f"{summary_text}\n\n{hbold(prompt_text)}"
    try:
        await callback.message.edit_text(full_message, reply_markup=keyboard, parse_mode="HTML")
    except Exception: # If message too long or other edit error
        await callback.message.answer(full_message, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "admin_prod_create_execute_add", StateFilter(AdminProductStates.PRODUCT_CONFIRM_ADD))
async def cq_admin_prod_create_execute_add(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    lang = user_data.get("language", "en")
    admin_id = callback.from_user.id
    user_service = UserService()
    product_service = ProductService()

    if not await is_admin_user_check(admin_id, user_service):
        return await callback.answer(get_text("admin_access_denied", lang), show_alert=True)

    state_data = await state.get_data()
    product_main_data = state_data.get("product_data", {})
    product_localizations = state_data.get("product_localizations_temp", [])

    # Re-check necessary data just in case
    if not product_main_data.get("manufacturer_id") or "cost" not in product_main_data or not product_localizations:
        await callback.answer(get_text("admin_prod_error_incomplete_data_for_creation", lang), show_alert=True)
        await state.clear() # Clear state as it's inconsistent
        # Send back to product menu
        prod_menu_text = get_text("admin_product_management_title", lang)
        prod_menu_kb = create_admin_product_management_menu_keyboard(lang)
        await callback.message.edit_text(prod_menu_text, reply_markup=prod_menu_kb)
        return

    created_product, message_key, product_id = await product_service.create_product_with_details(
        admin_id=admin_id,
        product_data=product_main_data,
        localizations_data=product_localizations,
        lang=lang
    )

    if created_product and product_id:
        # Get one of the names for the success message, preferably in admin's language or English
        product_display_name = product_main_data.get("sku", str(product_id)) # Fallback to SKU or ID
        for loc in product_localizations:
            if loc['language_code'] == lang:
                product_display_name = loc['name']
                break
            if loc['language_code'] == 'en' and product_display_name == product_main_data.get("sku", str(product_id)): # Prefer English over SKU if admin lang not found
                 product_display_name = loc['name']
        
        final_message = get_text(message_key, lang, product_name=hcode(product_display_name), product_id=product_id)
        await callback.answer(final_message, show_alert=True) # Show as alert for more visibility
    else:
        # Construct error message if specific details are available (e.g. SKU for duplicate error)
        error_sku = product_main_data.get('sku', 'N/A')
        final_message = get_text(message_key, lang, sku=hcode(error_sku))
        await callback.answer(final_message, show_alert=True)


    await state.clear() # Clear FSM state for product creation
    
    # Navigate back to product management menu
    prod_menu_text = get_text("admin_product_management_title", lang)
    prod_menu_kb = create_admin_product_management_menu_keyboard(lang)
    try:
        await callback.message.edit_text(prod_menu_text, reply_markup=prod_menu_kb)
    except Exception: # If edit fails (e.g. from alert being shown), send new.
        await callback.message.answer(prod_menu_text, reply_markup=prod_menu_kb)
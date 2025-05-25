"""
Inline keyboard generators for the Telegram bot.
Creates dynamic keyboards based on data and user language.
Includes keyboards for product selection, cart, ordering, and admin functions.
"""

import logging 
from typing import List, Dict, Any, Optional, Union 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.localization.locales import get_text, TEXTS as ALL_TEXTS 
from app.utils.helpers import OrderStatusEnum, get_order_status_emoji 
from app.utils.helpers import format_price 

logger = logging.getLogger(__name__) 

# Constants for pagination
ITEMS_PER_PAGE_ADMIN = 10 
ITEMS_PER_PAGE_USER = 6 


def create_language_keyboard(current_language: Optional[str] = None) -> InlineKeyboardMarkup: 
    """Create language selection keyboard."""
    builder = InlineKeyboardBuilder()
    
    supported_languages = sorted([lang_code for lang_code in ALL_TEXTS.get("language_name_en", {}).keys() if lang_code is not None])

    if not supported_languages: 
        supported_languages = ["en", "ru", "pl"]
        
    for lang_code in supported_languages:
        lang_display_text = get_text(f"language_name_{lang_code}", lang_code) 
        if lang_display_text.startswith('[[') or lang_display_text.startswith('['): 
            lang_display_text = lang_code.upper()
            
        emoji_map = {"en": "🇺🇸", "ru": "🇷🇺", "pl": "🇵🇱"}
        emoji = emoji_map.get(lang_code, "🌍")
        
        button_text = f"{emoji} {lang_display_text}"
        if current_language == lang_code:
            button_text = f"✅ {button_text}" 

        builder.button(text=button_text, callback_data=f"lang:{lang_code}")
    
    builder.adjust(2) 
    if current_language:
         builder.row(InlineKeyboardButton(text=get_text("back_to_menu", current_language), callback_data="main_menu"))
    return builder.as_markup()


def create_main_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    """Create main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("start_order", language), callback_data="start_order"))
    builder.row(
        InlineKeyboardButton(text=get_text("view_cart", language), callback_data="view_cart"),
        InlineKeyboardButton(text=get_text("my_orders", language), callback_data="my_orders")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("help", language), callback_data="show_help"),
        InlineKeyboardButton(text=get_text("change_language", language), callback_data="cmd_language") 
    )
    return builder.as_markup()


def create_locations_keyboard(locations: List[Dict[str, Any]], language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for location in locations: 
        builder.row(InlineKeyboardButton(text=location["name"], callback_data=f"location:{location['id']}"))
    builder.row(InlineKeyboardButton(text=get_text("back_to_menu", language), callback_data="main_menu"))
    return builder.as_markup()


def create_manufacturers_keyboard(manufacturers: List[Dict[str, Any]], language: str, back_callback: str = "start_order_from_mfg") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mfg in manufacturers: 
        builder.row(InlineKeyboardButton(text=mfg["name"], callback_data=f"manufacturer:{mfg['id']}"))
    builder.row(InlineKeyboardButton(text=get_text("back", language), callback_data=back_callback))
    return builder.as_markup()


def create_products_keyboard(products: List[Dict[str, Any]], language: str, back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        text = product["name"] 
        if product.get("variation"): text += f" ({product['variation']})"
        builder.row(InlineKeyboardButton(text=text, callback_data=f"product:{product['id']}"))
    builder.row(InlineKeyboardButton(text=get_text("back", language), callback_data=back_callback))
    return builder.as_markup()


def create_quantity_keyboard(max_quantity: int, language: str, back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    row_buttons = []
    quick_amounts = [1, 2, 3, 5, 10] 
    for amount in quick_amounts:
        if amount <= max_quantity:
            row_buttons.append(InlineKeyboardButton(text=str(amount), callback_data=f"qty:{amount}"))
    if row_buttons: builder.row(*row_buttons, width=len(row_buttons) if len(row_buttons) <= 3 else 3) 
    
    if max_quantity > 0 and max_quantity not in quick_amounts and max_quantity > (quick_amounts[-1] if quick_amounts else 0) :
         builder.add(InlineKeyboardButton(text=f"{get_text('max', language)} ({max_quantity})", callback_data=f"qty:{max_quantity}"))

    if max_quantity > 0: 
        builder.row(InlineKeyboardButton(text=get_text("custom_amount", language), callback_data="qty:custom"))
        
    builder.row(InlineKeyboardButton(text=get_text("back", language), callback_data=back_callback))
    return builder.as_markup()

def create_cart_keyboard(language: str, has_items: bool = False, is_empty: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_items: 
        builder.row(InlineKeyboardButton(text=get_text("checkout", language), callback_data="checkout"))
        builder.row(
            InlineKeyboardButton(text=get_text("manage_cart_items_button", language), callback_data="manage_cart_items"), 
            InlineKeyboardButton(text=get_text("clear_cart", language), callback_data="clear_cart")
        )
    builder.row(
        InlineKeyboardButton(text=get_text("continue_shopping", language), callback_data="start_order"),
        InlineKeyboardButton(text=get_text("main_menu_button", language), callback_data="main_menu")
    )
    return builder.as_markup()

def create_manage_cart_items_keyboard(cart_items: List[Dict[str, Any]], language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in cart_items:
        item_text = f"{item['name']} ({item['location_name']}) - {item['quantity']}x"
        builder.row(
            InlineKeyboardButton(text=item_text, callback_data=f"noop_cart_item_display:{item['product_id']}:{item['location_id']}"), 
        )
        builder.row(
            InlineKeyboardButton(text=get_text("cart_button_change_qty", language), callback_data=f"change_cart_item_qty:{item['product_id']}:{item['location_id']}"), 
            InlineKeyboardButton(text=get_text("cart_button_remove", language), callback_data=f"remove_cart_item:{item['product_id']}:{item['location_id']}") 
        )
    builder.row(InlineKeyboardButton(text=get_text("back_to_cart", language), callback_data="view_cart")) 
    return builder.as_markup()

def create_change_cart_item_quantity_keyboard(
    product_id: int, location_id: int, current_qty: int, max_stock: int, language: str
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    quick_changes = [1, 2, 5] 
    
    plus_buttons = []
    for change in quick_changes:
        new_qty_plus = current_qty + change
        if new_qty_plus <= max_stock:
            plus_buttons.append(InlineKeyboardButton(text=f"+{change}", callback_data=f"process_cart_qty_change:{product_id}:{location_id}:{new_qty_plus}"))
    if plus_buttons: builder.row(*plus_buttons)
    
    minus_buttons = []
    for change in quick_changes:
        new_qty_minus = current_qty - change
        if new_qty_minus >= 1: 
            minus_buttons.append(InlineKeyboardButton(text=f"-{change}", callback_data=f"process_cart_qty_change:{product_id}:{location_id}:{new_qty_minus}"))
    if minus_buttons: builder.row(*minus_buttons)

    specific_quantities = sorted(list(set([q for q in [1, current_qty // 2 if current_qty > 1 else 0 , max_stock] if 0 < q <= max_stock and q != current_qty])))
    specific_quantity_buttons = []
    for qty_val in specific_quantities:
         if qty_val > 0: 
             specific_quantity_buttons.append(InlineKeyboardButton(text=str(qty_val), callback_data=f"process_cart_qty_change:{product_id}:{location_id}:{qty_val}"))
    if specific_quantity_buttons:
         builder.row(*specific_quantity_buttons, width=len(specific_quantity_buttons))
         
    if max_stock > 0: 
        builder.row(InlineKeyboardButton(text=get_text("custom_amount", language), callback_data=f"process_cart_qty_change:{product_id}:{location_id}:custom"))
    
    builder.row(InlineKeyboardButton(text=get_text("cart_button_remove", language), callback_data=f"remove_cart_item:{product_id}:{location_id}"))
    builder.row(InlineKeyboardButton(text=get_text("back_to_manage_cart", language), callback_data="manage_cart_items")) 
    return builder.as_markup()


def create_payment_methods_keyboard(language: str, back_callback: str = "view_cart") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("payment_cash", language), callback_data="payment:cash"))
    builder.row(InlineKeyboardButton(text=get_text("payment_card", language), callback_data="payment:card"))
    builder.row(InlineKeyboardButton(text=get_text("back", language), callback_data=back_callback))
    return builder.as_markup()

def create_confirm_order_keyboard(language: str, back_callback: str = "checkout") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("confirm_order", language), callback_data="confirm_order"),
        InlineKeyboardButton(text=get_text("cancel_order_confirmation", language), callback_data="cancel_order_confirmation")
    )
    builder.row(InlineKeyboardButton(text=get_text("back", language), callback_data=back_callback))
    return builder.as_markup()

def create_back_to_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("main_menu_button", language), callback_data="main_menu"))
    return builder.as_markup()

def create_back_button(text_key: str, language: str, callback_data: str) -> InlineKeyboardButton: 
    return InlineKeyboardButton(text=get_text(text_key, language), callback_data=callback_data)

# --- Admin Keyboards ---
def create_admin_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("admin_orders_button", language), callback_data="admin_orders_menu"),
        InlineKeyboardButton(text=get_text("admin_products_button", language), callback_data="admin_products_menu")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("admin_users_button", language), callback_data="admin_users_menu"),
        InlineKeyboardButton(text=get_text("admin_stock_management_button", language), callback_data="admin_stock_menu")
    )
    builder.row( # Grouping other management for brevity, can be split
        InlineKeyboardButton(text=get_text("admin_categories_button", language), callback_data="admin_categories_menu"),
        InlineKeyboardButton(text=get_text("admin_manufacturers_button", language), callback_data="admin_manufacturers_menu"),
        InlineKeyboardButton(text=get_text("admin_locations_button", language), callback_data="admin_locations_menu")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("admin_settings_button", language), callback_data="admin_settings_menu"), 
        InlineKeyboardButton(text=get_text("admin_stats_button", language), callback_data="admin_stats_menu") 
    )
    builder.row(create_back_button("main_menu_button", language, "main_menu")) 
    return builder.as_markup()

def create_admin_order_list_filters_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    pending_display = get_text(f"order_status_{OrderStatusEnum.PENDING_ADMIN_APPROVAL.value}", language)
    approved_display = get_text(f"order_status_{OrderStatusEnum.APPROVED.value}", language)
    all_display = get_text("admin_filter_all_orders_display", language)

    builder.row(InlineKeyboardButton(text=f"⏳ {pending_display}", callback_data=f"admin_orders_filter:{OrderStatusEnum.PENDING_ADMIN_APPROVAL.value}"))
    builder.row(InlineKeyboardButton(text=f"✅ {approved_display}", callback_data=f"admin_orders_filter:{OrderStatusEnum.APPROVED.value}"))
    # Add more common filters if needed, e.g., completed, cancelled
    builder.row(InlineKeyboardButton(text=f"🧾 {all_display}", callback_data="admin_orders_filter:all"))
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()

def create_admin_order_actions_keyboard(order_id: int, current_status_raw: str, language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if current_status_raw == OrderStatusEnum.PENDING_ADMIN_APPROVAL.value:
        builder.row(
            InlineKeyboardButton(text="✅ " + get_text("approve_order", language), callback_data=f"admin_approve_order:{order_id}"),
            InlineKeyboardButton(text="🚫 " + get_text("reject_order", language), callback_data=f"admin_reject_order:{order_id}")
        )
    
    if current_status_raw in [
        OrderStatusEnum.APPROVED.value, OrderStatusEnum.PROCESSING.value, 
        OrderStatusEnum.READY_FOR_PICKUP.value, OrderStatusEnum.SHIPPED.value
    ]: # Non-final, cancellable states
        builder.row(InlineKeyboardButton(text="❌ " + get_text("admin_action_cancel_order", language), callback_data=f"admin_cancel_order:{order_id}"))

    # Allow changing status unless it's already completed, cancelled or rejected
    if current_status_raw not in [OrderStatusEnum.COMPLETED.value, OrderStatusEnum.CANCELLED.value, OrderStatusEnum.REJECTED.value]:
         builder.row(InlineKeyboardButton(text="🔄 " + get_text("admin_action_change_status", language), callback_data=f"admin_change_order_status:{order_id}"))

    # Determine the filter for the "Back to Orders List" button
    # If current_status_raw is a valid enum value, use it for the filter, otherwise default to 'all'
    back_filter = current_status_raw if current_status_raw in OrderStatusEnum.values() else 'all'
    builder.row(create_back_button("back_to_orders_list", language, f"admin_orders_filter:{back_filter}"))
    return builder.as_markup()

def create_admin_order_statuses_keyboard(language: str, current_status_raw: str, order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for status in OrderStatusEnum:
        if status.value == current_status_raw: continue 
        
        # Simplified: Allow changing to any other status. Service layer should validate transitions.
        # if current_status_raw in [OrderStatusEnum.COMPLETED.value, OrderStatusEnum.CANCELLED.value, OrderStatusEnum.REJECTED.value] and \
        #    status not in [OrderStatusEnum.COMPLETED, OrderStatusEnum.CANCELLED, OrderStatusEnum.REJECTED]: 
        #     continue 

        emoji = get_order_status_emoji(status.value)
        builder.row(InlineKeyboardButton(
            text=f"{emoji} {get_text(f'order_status_{status.value}', language)}", 
            callback_data=f"admin_set_status:{order_id}:{status.value}"
        ))
    builder.row(create_back_button("back", language, f"admin_order_details:{order_id}")) 
    return builder.as_markup()


def create_paginated_keyboard(
    items: List[Dict[str, Any]], 
    page: int, 
    items_per_page: int, 
    base_callback_data: str, # e.g., "admin_users_list_page:all" (filter part included)
    item_callback_prefix: str, # e.g., "admin_user_details"
    language: str,
    back_callback_key: str, 
    back_callback_data: str, 
    additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
    item_text_key: Optional[str] = "name", # Default to 'name' if items are dicts with a name field
    total_items_override: Optional[int] = None, # If provided, `items` is assumed to be for current page only
    item_id_key: str = 'id' 
    ) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    total_items = total_items_override if total_items_override is not None else len(items)
    
    # If total_items_override is not None, items is already the slice for the current page.
    # Otherwise, items is the full list, and we need to slice it.
    visible_items = items if total_items_override is not None else items[page * items_per_page : (page + 1) * items_per_page]

    if not isinstance(visible_items, list): 
        logger.warning(f"create_paginated_keyboard received non-list visible_items: {type(visible_items)}")
        visible_items = [] 

    for item in visible_items:
        button_text = "Unknown Item" 
        item_id = item.get(item_id_key) 
        if item_id is None: 
            logger.error(f"Item in paginated list missing '{item_id_key}' key: {item}")
            continue 

        if item_text_key and item_text_key in item: 
            button_text = str(item[item_text_key]) 
        elif "name" in item: 
            button_text = str(item["name"])
        elif item_id_key in item: 
            button_text = f"{get_text('id_prefix', language, default='ID')}: {item_id}" 
        
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"{item_callback_prefix}:{item_id}"))

    pagination_buttons_row = []
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if page > 0:
        # base_callback_data might be "admin_users_list_page:all" or "admin_users_list_page:blocked"
        # We need to append the page number after this base.
        pagination_buttons_row.append(InlineKeyboardButton(text=get_text("prev_page", language), callback_data=f"{base_callback_data}:{page-1}"))
    
    if total_pages > 1: 
         pagination_buttons_row.append(InlineKeyboardButton(text=get_text("page_display", language).format(current_page=page+1, total_pages=total_pages), callback_data="noop_page_display"))

    if (page + 1) < total_pages : # Check if there is a next page
        pagination_buttons_row.append(InlineKeyboardButton(text=get_text("next_page", language), callback_data=f"{base_callback_data}:{page+1}"))
    
    if pagination_buttons_row:
        builder.row(*pagination_buttons_row)

    if additional_buttons:
        for row_of_buttons in additional_buttons:
            builder.row(*row_of_buttons)
            
    builder.row(create_back_button(back_callback_key, language, back_callback_data))
    return builder.as_markup()


def create_admin_product_management_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_action_add", language), callback_data="admin_prod_add_start")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list", language), callback_data="admin_prod_list:0")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_edit", language), callback_data="admin_prod_edit_select:0")) 
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()

def create_admin_category_management_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_action_add", language), callback_data="admin_cat_add_start")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list", language), callback_data="admin_cat_list:0"))
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()

def create_admin_manufacturer_management_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_action_add", language), callback_data="admin_mfg_add_start")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list", language), callback_data="admin_mfg_list:0"))
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()
    
def create_admin_location_management_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_action_add", language), callback_data="admin_loc_add_start")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list", language), callback_data="admin_loc_list:0"))
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()
    
def create_admin_stock_management_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_action_update_stock", language), callback_data="admin_stock_select_prod:0")) 
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()

def create_admin_user_management_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Base callback for pagination will include the filter type
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list_all_users", language), callback_data="admin_users_list_page:all:0")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list_blocked_users", language), callback_data="admin_users_list_page:blocked:0")) 
    builder.row(InlineKeyboardButton(text=get_text("admin_action_list_active_users", language), callback_data="admin_users_list_page:active:0"))
    # TODO: Add button for searching users by ID/username: callback_data="admin_user_search_prompt"
    builder.row(create_back_button("back_to_admin_main_menu", language, "admin_panel_main"))
    return builder.as_markup()

def create_admin_user_list_item_keyboard(telegram_id: int, is_blocked: bool, language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Callback for user orders would be: f"admin_orders_filter_user:{telegram_id}:all:0" or similar
    # For now, this button is illustrative as its handler is not fully implemented here.
    # builder.row(InlineKeyboardButton(text=get_text("admin_action_view_orders", language), callback_data=f"admin_view_user_orders:{telegram_id}:0")) 

    if is_blocked:
        builder.row(InlineKeyboardButton(text=get_text("admin_action_unblock_user", language), callback_data=f"admin_user_unblock_confirm_prompt:{telegram_id}"))
    else:
        builder.row(InlineKeyboardButton(text=get_text("admin_action_block_user", language), callback_data=f"admin_user_block_confirm_prompt:{telegram_id}"))

    builder.row(create_back_button("back_to_user_list", language, "back_to_user_list")) 
    return builder.as_markup()


def create_confirmation_keyboard(language: str, yes_callback: str, no_callback: str, 
                                 yes_text_key: str = "yes", no_text_key: str = "cancel") -> InlineKeyboardMarkup: 
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text(yes_text_key, language), callback_data=yes_callback),
        InlineKeyboardButton(text=get_text(no_text_key, language), callback_data=no_callback)
    )
    return builder.as_markup()

def create_admin_product_edit_options_keyboard(product_id: int, language: str, product_name: str) -> InlineKeyboardMarkup: 
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_manufacturer_id", language), callback_data=f"admin_prod_edit_field:{product_id}:manufacturer_id"))
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_category_id", language), callback_data=f"admin_prod_edit_field:{product_id}:category_id"))
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_cost", language), callback_data=f"admin_prod_edit_field:{product_id}:cost"))
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_sku", language), callback_data=f"admin_prod_edit_field:{product_id}:sku"))
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_variation", language), callback_data=f"admin_prod_edit_field:{product_id}:variation"))
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_image_url", language), callback_data=f"admin_prod_edit_field:{product_id}:image_url"))
    builder.row(InlineKeyboardButton(text=get_text("product_field_name_localizations", language), callback_data=f"admin_prod_edit_locs_menu:{product_id}"))
    builder.row(InlineKeyboardButton(text=get_text("admin_action_update_stock", language), callback_data=f"admin_stock_select_loc_for_prod:{product_id}:0")) 
    builder.row(create_back_button("back_to_admin_products_menu", language, "admin_prod_list:0")) 
    return builder.as_markup()
    
def create_admin_localization_actions_keyboard(product_id: int, localizations: List[Dict[str,str]], language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sorted_localizations = sorted(localizations, key=lambda x: x.get('lang_code', '')) 
    
    for loc in sorted_localizations: 
        lang_code = loc.get('lang_code', 'unknown')
        loc_name = loc.get('name', get_text('not_set', language)) 
        lang_display = get_text(f"language_name_{lang_code}", language) 
        if lang_display.startswith('[[') or lang_display.startswith('['):
             lang_display = lang_code.upper()
        
        builder.row(InlineKeyboardButton(text=f"✏️ {lang_display}: {loc_name}", callback_data=f"admin_prod_edit_loc_select:{product_id}:{lang_code}"))
    
    builder.row(InlineKeyboardButton(text="➕ " + get_text("admin_action_add_localization", language), callback_data=f"admin_prod_add_loc_start:{product_id}")) 
    builder.row(create_back_button("back", language, f"admin_prod_options:{product_id}")) 
    return builder.as_markup()

def create_admin_select_lang_for_localization_keyboard(product_id: int, action_prefix: str, language: str, existing_lang_codes: List[str]) -> InlineKeyboardMarkup: 
    builder = InlineKeyboardBuilder()

    supported_languages = sorted([lang_code for lang_code in ALL_TEXTS.get("language_name_en", {}).keys() if lang_code is not None])
    if not supported_languages: supported_languages = ["en", "ru", "pl"]
    
    available_langs_for_new_loc = [lc for lc in supported_languages if lc not in existing_lang_codes]

    if not available_langs_for_new_loc:
        pass 

    for lang_code in available_langs_for_new_loc:
        lang_display = get_text(f"language_name_{lang_code}", language)
        if lang_display.startswith('[[') or lang_display.startswith('['):
             lang_display = lang_code.upper()
             
        builder.button(text=lang_display, callback_data=f"{action_prefix}:{product_id}:{lang_code}")
    
    if available_langs_for_new_loc: builder.adjust(2)

    back_cb = f"admin_prod_edit_locs_menu:{product_id}" 
    builder.row(create_back_button("cancel", language, back_cb))
    return builder.as_markup()

def create_admin_stock_locations_keyboard(product_id: int, locations_data: List[Dict[str, Any]], language: str, page: int = 0) -> InlineKeyboardMarkup: 
    builder = InlineKeyboardBuilder()
    if not locations_data:
        builder.row(InlineKeyboardButton(text=get_text("no_stock_records_for_product", language), callback_data="noop_no_stock")) 
    
    for loc_data in locations_data: 
        button_text = f"{loc_data.get('name', get_text('unknown_location_name', language))} ({loc_data.get('quantity', 0)} {get_text('units_short', language)})"
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"admin_stock_update_selected_loc:{product_id}:{loc_data['id']}")) 
                                        
    builder.row(create_back_button("back_to_product_options", language, f"admin_prod_options:{product_id}")) 
    return builder.as_markup()




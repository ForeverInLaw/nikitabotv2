"""
User handlers for the main shopping flow: product selection, cart management, ordering.
Implements the complete user journey from product browsing to order completion.
"""

import logging
from typing import Any, Dict, Union
from decimal import Decimal

from aiogram import Router, types, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.utils.markdown import hbold, hitalic

from app.keyboards.inline import (
    create_locations_keyboard, 
    create_manufacturers_keyboard,
    create_products_keyboard,
    create_quantity_keyboard,
    create_cart_keyboard,
    create_payment_methods_keyboard,
    create_confirm_order_keyboard,
    create_back_to_menu_keyboard,
    create_main_menu_keyboard, 
    create_manage_cart_items_keyboard, 
    create_change_cart_item_quantity_keyboard 
)
from app.services.product_service import ProductService
from app.services.order_service import OrderService
from app.localization.locales import get_text
from app.utils.helpers import format_price, format_datetime, get_order_status_emoji, validate_quantity as validate_qty_util

logger = logging.getLogger(__name__)
router = Router()


class OrderStates(StatesGroup):
    """States for the ordering process."""
    choosing_location = State()
    choosing_manufacturer = State()
    choosing_product = State()
    entering_quantity = State()
    
    viewing_cart = State()
    managing_cart_items = State() 
    editing_cart_item_quantity = State() 

    choosing_payment = State()
    confirming_order = State()
    viewing_order_history = State() 
    viewing_order_detail = State() 


async def _go_to_main_menu(event: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any]):
    await state.clear()
    language = user_data.get("language", "en")
    text = get_text("main_menu", language)
    keyboard = create_main_menu_keyboard(language) # Inline keyboard
    
    if isinstance(event, types.Message):
        await event.answer(text, reply_markup=keyboard)
    elif isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=keyboard)
        except Exception: # If message can't be edited (e.g., it was a response to FSM text input)
            await event.message.answer(text, reply_markup=keyboard) # Send as new message
        await event.answer()


@router.callback_query(F.data == "start_order", StateFilter(default_state, None, OrderStates.viewing_cart)) # Allow from cart too
async def start_order_entry(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    product_service = ProductService()
    
    locations = await product_service.get_locations_with_stock(language) # Pass language for potential name localization if any
    if not locations:
        await callback.message.edit_text(
            get_text("no_locations_available", language),
            reply_markup=create_back_to_menu_keyboard(language)
        )
        await callback.answer()
        return
    
    await state.set_state(OrderStates.choosing_location)
    
    await callback.message.edit_text(
        get_text("choose_location", language),
        reply_markup=create_locations_keyboard(locations, language)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started ordering (state: {await state.get_state()}). Lang: {language}")


@router.callback_query(StateFilter(OrderStates.choosing_location), F.data.startswith("location:"))
async def select_location_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    location_id = int(callback.data.split(":")[1])
    await state.update_data(location_id=location_id)
    
    product_service = ProductService()
    # Manufacturer names are assumed to be language-neutral from DB or handled by ProductService if they can be localized
    manufacturers = await product_service.get_manufacturers_by_location(location_id, language) # Pass language
    
    if not manufacturers:
        locations = await product_service.get_locations_with_stock(language) 
        await callback.message.edit_text(
            get_text("no_manufacturers_available", language),
            reply_markup=create_locations_keyboard(locations, language) 
        )
        await callback.answer(get_text("no_manufacturers_available", language), show_alert=True)
        return

    # Fetch location name for message - ProductService should provide this, ideally localized if applicable
    location_details = await product_service.get_location_by_id(location_id) # Assume name is not localized or handled by service
    location_name = location_details.name if location_details else get_text("unknown_location_name", language)

    await state.set_state(OrderStates.choosing_manufacturer)
    await callback.message.edit_text(
        get_text("choose_manufacturer", language).format(location=location_name),
        reply_markup=create_manufacturers_keyboard(manufacturers, language, back_callback="start_order_from_mfg") 
    )
    await callback.answer()

# Combined back handler for product flow
@router.callback_query(StateFilter(OrderStates.choosing_manufacturer, OrderStates.choosing_product, OrderStates.entering_quantity), 
                       F.data.in_({"start_order_from_mfg"})) # Back to location selection
async def back_to_locations_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    await state.set_state(OrderStates.choosing_location) 
    await start_order_entry(callback, state, user_data) 


@router.callback_query(StateFilter(OrderStates.choosing_manufacturer), F.data.startswith("manufacturer:"))
async def select_manufacturer_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    manufacturer_id = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    location_id = state_data.get("location_id")

    if location_id is None: 
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        return await _go_to_main_menu(callback, state, user_data)

    await state.update_data(manufacturer_id=manufacturer_id)
    product_service = ProductService()
    # Products are fetched with localized names by ProductService
    products = await product_service.get_products_by_manufacturer_and_location(manufacturer_id, location_id, language)

    manufacturer_details = await product_service.get_manufacturer_by_id(manufacturer_id) # Name assumed not localized or handled by service
    mfg_name = manufacturer_details.name if manufacturer_details else get_text("unknown_manufacturer_name", language)

    if not products:
        manufacturers = await product_service.get_manufacturers_by_location(location_id, language) 
        location_details = await product_service.get_location_by_id(location_id)
        location_name = location_details.name if location_details else get_text("unknown_location_name", language)
        
        await callback.message.edit_text(
            get_text("no_products_available_manufacturer_location", language).format(manufacturer=mfg_name),
            reply_markup=create_manufacturers_keyboard(manufacturers, language, back_callback="start_order_from_mfg")
        )
        await callback.answer(get_text("no_products_available", language), show_alert=True)
        return

    await state.set_state(OrderStates.choosing_product)
    await callback.message.edit_text(
        get_text("choose_product", language).format(manufacturer=mfg_name), 
        reply_markup=create_products_keyboard(products, language, back_callback=f"back_to_mfg_list:{location_id}")
    )
    await callback.answer()

@router.callback_query(StateFilter(OrderStates.choosing_product, OrderStates.entering_quantity), F.data.startswith("back_to_mfg_list:"))
async def back_to_manufacturers_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    location_id = int(callback.data.split(":")[1]) 

    await state.update_data(location_id=location_id) # Ensure location_id is in state for select_location_handler logic
    
    # Simulate select_location_handler's end part
    product_service = ProductService()
    manufacturers = await product_service.get_manufacturers_by_location(location_id, language)
    
    location_details = await product_service.get_location_by_id(location_id)
    location_name = location_details.name if location_details else get_text("unknown_location_name", language)

    if not manufacturers: 
        await start_order_entry(callback, state, user_data) 
        return

    await state.set_state(OrderStates.choosing_manufacturer)
    await callback.message.edit_text(
        get_text("choose_manufacturer", language).format(location=location_name),
        reply_markup=create_manufacturers_keyboard(manufacturers, language, back_callback="start_order_from_mfg")
    )
    await callback.answer()


@router.callback_query(StateFilter(OrderStates.choosing_product), F.data.startswith("product:"))
async def select_product_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    product_id = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    location_id = state_data.get("location_id")
    manufacturer_id = state_data.get("manufacturer_id") 

    if location_id is None or manufacturer_id is None:
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        return await _go_to_main_menu(callback, state, user_data)

    await state.update_data(product_id=product_id)
    product_service = ProductService()
    product_details = await product_service.get_product_details(product_id, location_id, language) 

    if not product_details or product_details["stock"] <= 0:
        products = await product_service.get_products_by_manufacturer_and_location(manufacturer_id, location_id, language)
        manufacturer_details = await product_service.get_manufacturer_by_id(manufacturer_id)
        mfg_name = manufacturer_details.name if manufacturer_details else get_text("unknown_manufacturer_name", language)
        
        await callback.message.edit_text(
            get_text("product_out_of_stock", language),
            reply_markup=create_products_keyboard(products, language, back_callback=f"back_to_mfg_list:{location_id}")
        )
        await callback.answer(get_text("product_out_of_stock", language), show_alert=True)
        return
    
    # Product name and description are already localized by ProductService
    text = get_text("product_details", language).format(
        name=product_details["name"],
        description=product_details.get("description", ""),
        price=format_price(product_details["price"]), # format_price is language-neutral for currency symbol
        stock=product_details["stock"],
        units_short=get_text("units_short", language)
    )
    await state.set_state(OrderStates.entering_quantity)
    await callback.message.edit_text(
        text,
        reply_markup=create_quantity_keyboard(product_details["stock"], language, back_callback=f"back_to_prod_list:{manufacturer_id}:{location_id}"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(StateFilter(OrderStates.entering_quantity), F.data.startswith("back_to_prod_list:"))
async def back_to_products_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    parts = callback.data.split(":")
    manufacturer_id = int(parts[1])
    location_id = int(parts[2])

    await state.update_data(manufacturer_id=manufacturer_id, location_id=location_id)
    product_service = ProductService()
    products = await product_service.get_products_by_manufacturer_and_location(manufacturer_id, location_id, language)

    manufacturer_details = await product_service.get_manufacturer_by_id(manufacturer_id)
    mfg_name = manufacturer_details.name if manufacturer_details else get_text("unknown_manufacturer_name", language)

    if not products: 
        # This simulates going back one more step to manufacturer list
        mock_cb_data = f"back_to_mfg_list:{location_id}"
        # Create a mock callback object if necessary or reuse parts of back_to_manufacturers_handler
        await state.set_state(OrderStates.choosing_manufacturer) # Set state correctly
        # Re-fetch manufacturers for the location
        manufacturers = await product_service.get_manufacturers_by_location(location_id, language)
        location_details = await product_service.get_location_by_id(location_id)
        location_name = location_details.name if location_details else get_text("unknown_location_name", language)
        await callback.message.edit_text(
            get_text("choose_manufacturer", language).format(location=location_name),
            reply_markup=create_manufacturers_keyboard(manufacturers, language, back_callback="start_order_from_mfg")
        )
        await callback.answer()
        return

    await state.set_state(OrderStates.choosing_product)
    await callback.message.edit_text(
        get_text("choose_product", language).format(manufacturer=mfg_name),
        reply_markup=create_products_keyboard(products, language, back_callback=f"back_to_mfg_list:{location_id}")
    )
    await callback.answer()


@router.callback_query(StateFilter(OrderStates.entering_quantity), F.data.startswith("qty:"))
async def quantity_selected_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    
    if callback.data == "qty:custom":
        # Add cancel prompt with localized text
        cancel_text = get_text("cancel_prompt", language)
        await callback.message.edit_text(
             get_text("enter_custom_quantity", language) + f"\n\n{hitalic(cancel_text)}"
        )
        await callback.answer()
        return 

    quantity = int(callback.data.split(":")[1])
    await _process_add_to_cart(callback, state, user_data, quantity) # Pass callback directly


@router.message(StateFilter(OrderStates.entering_quantity), F.text)
async def custom_quantity_entered_handler(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    
    # Universal cancel check for text inputs in FSM
    if message.text.lower() == "/cancel": # Or check against localized cancel command
        await universal_cancel_message(message, state, user_data) # Reuse cancel handler
        return

    quantity = validate_qty_util(message.text)
    state_data = await state.get_data() # Get current FSM data
    product_id = state_data.get("product_id")
    location_id = state_data.get("location_id")
    manufacturer_id = state_data.get("manufacturer_id")

    if not all([product_id, location_id, manufacturer_id]):
         await message.answer(get_text("error_occurred", language))
         return await _go_to_main_menu(message, state, user_data)

    if quantity is None: # Invalid quantity input
        # Re-prompt for custom quantity, including original product details and quantity keyboard
        product_service = ProductService()
        product_details = await product_service.get_product_details(product_id, location_id, language)
        
        if not product_details: 
            await message.answer(get_text("error_occurred", language))
            return await _go_to_main_menu(message, state, user_data)

        # Format product details text again
        details_text = get_text("product_details", language).format(
            name=product_details["name"], description=product_details.get("description", ""),
            price=format_price(product_details["price"]), stock=product_details["stock"],
            units_short=get_text("units_short", language)
        )
        # Add invalid quantity message and re-prompt
        prompt_text = get_text("invalid_quantity", language) + "\n" + get_text("enter_custom_quantity", language)
        cancel_text = get_text("cancel_prompt", language)
        
        full_message = f"{details_text}\n\n{hbold(prompt_text)}\n{hitalic(cancel_text)}"
        
        await message.answer(
             full_message,
             reply_markup=create_quantity_keyboard(product_details["stock"], language, back_callback=f"back_to_prod_list:{manufacturer_id}:{location_id}"),
             parse_mode="HTML"
        )
        return 

    await _process_add_to_cart(message, state, user_data, quantity) # Pass message directly


async def _process_add_to_cart(event: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any], quantity: int):
    language = user_data.get("language", "en")
    state_data = await state.get_data()
    product_id = state_data.get("product_id")
    location_id = state_data.get("location_id")
    manufacturer_id = state_data.get("manufacturer_id") # For back button context if add fails

    if not all([product_id, location_id, manufacturer_id]):
        # Use event.answer for callbacks, event.reply for messages if needed
        response_method = event.answer if isinstance(event, types.CallbackQuery) else event.answer
        await response_method(get_text("error_occurred", language), show_alert=isinstance(event, types.CallbackQuery))
        return await _go_to_main_menu(event, state, user_data)

    order_service = OrderService()
    # The add_to_cart in OrderService expects quantity_to_add. 
    # If we want to set the total, the service method needs to be designed for that, or we fetch current cart qty.
    # Assuming this 'quantity' is the *total desired quantity for this item in the cart now*.
    # The OrderService method `update_cart_item_quantity` is more suitable for this logic.
    success, message_key_or_error = await order_service.update_cart_item_quantity(
        user_id=event.from_user.id, 
        product_id=product_id, 
        location_id=location_id, 
        new_quantity=quantity, 
        language=language
    )
    
    # Determine how to respond (edit message for callback, new message for text input)
    response_target = event.message if isinstance(event, types.CallbackQuery) else event
    alert_text = get_text(message_key_or_error, language) if success else message_key_or_error

    if isinstance(event, types.CallbackQuery): 
        await event.answer(alert_text, show_alert=not success) # Show alert for callbacks

    if success:
        await state.set_state(OrderStates.viewing_cart)
        cart_has_items = bool(await order_service.get_cart_contents(event.from_user.id, language)) 
        cart_kb = create_cart_keyboard(language, has_items=cart_has_items)
        
        success_msg_text = get_text("added_to_cart", language) # Key for "Cart updated!"
        
        if isinstance(response_target, types.Message) and response_target.message_id == event.message_id and hasattr(response_target, 'edit_text'):
            await response_target.edit_text(success_msg_text, reply_markup=cart_kb)
        else: # New message or different message context
            await response_target.answer(success_msg_text, reply_markup=cart_kb)

    else: # Add to cart failed
        # Re-show product details and quantity keyboard with the error message
        product_service = ProductService()
        product_details = await product_service.get_product_details(product_id, location_id, language)
        
        if not product_details:
             await response_target.answer(get_text("error_occurred", language))
             return await _go_to_main_menu(event, state, user_data)
        
        details_text = get_text("product_details", language).format(
            name=product_details["name"], description=product_details.get("description", ""),
            price=format_price(product_details["price"]), stock=product_details["stock"],
            units_short=get_text("units_short", language)
        )
        # Error text is already localized `alert_text`
        full_message = f"{details_text}\n\n{hbold('⚠️ ' + alert_text)}" 
        
        quantity_keyboard = create_quantity_keyboard(product_details["stock"], language, back_callback=f"back_to_prod_list:{manufacturer_id}:{location_id}")

        if isinstance(response_target, types.Message) and response_target.message_id == event.message_id and hasattr(response_target, 'edit_text'):
            await response_target.edit_text(full_message, reply_markup=quantity_keyboard, parse_mode="HTML")
        else:
            await response_target.answer(full_message, reply_markup=quantity_keyboard, parse_mode="HTML")


# --- Cart Handlers ---
async def _display_cart(event_target: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    user_id = user_data.get("user_id")
    order_service = OrderService()
    cart_items = await order_service.get_cart_contents(user_id, language) 

    if not cart_items:
        text = get_text("cart_empty", language)
        kb = create_cart_keyboard(language, is_empty=True) # has_items=False
    else:
        text = hbold(get_text("cart_contents", language)) + "\n\n"
        total_cart_value = Decimal('0')
        for item in cart_items: # item name, variation, location_name are localized by OrderService
            item_total = item["price"] * item["quantity"]
            total_cart_value += item_total
            text += get_text("cart_item_format_user", language).format( 
                name=item["name"],
                variation=f" ({item['variation']})" if item.get("variation") else "",
                quantity=item["quantity"],
                price_each=format_price(item["price"]),
                price_total=format_price(item_total),
                location=item["location_name"]
            ) + "\n\n" # Double newline for spacing
        text += get_text("cart_total", language).format(total=format_price(total_cart_value))
        kb = create_cart_keyboard(language, has_items=True) 
    
    await state.set_state(OrderStates.viewing_cart)
    
    if isinstance(event_target, types.Message):
        await event_target.answer(text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(event_target, types.CallbackQuery):
        try:
            await event_target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await event_target.message.answer(text, reply_markup=kb, parse_mode="HTML") # If edit fails
        await event_target.answer()


@router.message(Command("cart"), StateFilter("*")) # Allow from any state, including FSM
async def cmd_view_cart(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    # If in a state, confirm if user wants to cancel current FSM action to view cart?
    # For now, just show cart and set state to viewing_cart.
    # await state.set_state(OrderStates.viewing_cart) # Let _display_cart handle state
    await _display_cart(message, state, user_data)

@router.callback_query(F.data == "view_cart", StateFilter("*")) 
async def cb_view_cart(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    # await state.set_state(OrderStates.viewing_cart) # Let _display_cart handle state
    await _display_cart(callback, state, user_data)


@router.callback_query(StateFilter(OrderStates.viewing_cart), F.data == "clear_cart")
async def clear_cart_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    order_service = OrderService()
    success = await order_service.clear_cart(callback.from_user.id)
    if success:
        await callback.answer(get_text("cart_cleared", language), show_alert=True)
    else:
        await callback.answer(get_text("failed_to_clear_cart", language), show_alert=True) # Should be rare
    await _display_cart(callback, state, user_data) 

@router.callback_query(StateFilter(OrderStates.viewing_cart), F.data == "manage_cart_items")
async def manage_cart_items_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    order_service = OrderService()
    cart_items = await order_service.get_cart_contents(callback.from_user.id, language) 

    if not cart_items:
        await callback.answer(get_text("cart_empty_alert", language), show_alert=True)
        return await _display_cart(callback, state, user_data) 
    
    await state.set_state(OrderStates.managing_cart_items)
    await callback.message.edit_text(
        get_text("manage_cart_items_title", language), 
        reply_markup=create_manage_cart_items_keyboard(cart_items, language) 
    )
    await callback.answer()

@router.callback_query(StateFilter(OrderStates.managing_cart_items), F.data.startswith("remove_cart_item:"))
async def remove_specific_cart_item_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    try:
        _, product_id_str, location_id_str = callback.data.split(":")
        product_id, location_id = int(product_id_str), int(location_id_str)
    except ValueError:
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        return

    order_service = OrderService()
    success, msg_key = await order_service.remove_from_cart(callback.from_user.id, product_id, location_id, language)
    await callback.answer(get_text(msg_key, language), show_alert=not success)
    
    cart_items = await order_service.get_cart_contents(callback.from_user.id, language) 
    if not cart_items: 
        return await _display_cart(callback, state, user_data)
    
    # Refresh manage_cart_items_keyboard
    await callback.message.edit_text(
        get_text("manage_cart_items_title", language),
        reply_markup=create_manage_cart_items_keyboard(cart_items, language) 
    )

@router.callback_query(StateFilter(OrderStates.managing_cart_items), F.data.startswith("change_cart_item_qty:"))
async def change_specific_cart_item_qty_prompt(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    try:
        _, product_id_str, location_id_str = callback.data.split(":")
        product_id, location_id = int(product_id_str), int(location_id_str)
    except ValueError:
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        return

    product_service = ProductService()
    order_service = OrderService()
    
    product_details = await product_service.get_product_details(product_id, location_id, language) 
    cart_item = await order_service.get_cart_item_details( # New specific method needed in OrderService
        user_id=callback.from_user.id, 
        product_id=product_id, 
        location_id=location_id, 
        language=language
    )

    if not product_details or not cart_item:
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        # Go back to manage cart if item somehow disappeared or error
        cart_contents = await order_service.get_cart_contents(callback.from_user.id, language)
        if not cart_contents: return await _display_cart(callback, state, user_data) # To empty cart view
        await callback.message.edit_text(get_text("manage_cart_items_title", language), reply_markup=create_manage_cart_items_keyboard(cart_contents, language))
        return

    await state.set_state(OrderStates.editing_cart_item_quantity)
    # Store identifiers for FSM message handler
    await state.update_data(editing_cart_product_id=product_id, editing_cart_location_id=location_id, 
                            editing_cart_product_name=product_details["name"], editing_cart_current_qty=cart_item["quantity"],
                            editing_cart_max_stock=product_details["stock"])
    
    # product_details["name"] is already localized
    prompt_text = get_text("cart_change_item_qty_prompt", language).format(product_name=product_details["name"], current_qty=cart_item["quantity"])
    cancel_text = get_text("cancel_prompt", language)
    
    await callback.message.edit_text(
        f"{prompt_text}\n\n{hitalic(cancel_text)}",
        reply_markup=create_change_cart_item_quantity_keyboard(product_id, location_id, cart_item["quantity"], product_details["stock"], language),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(StateFilter(OrderStates.editing_cart_item_quantity), F.text)
async def process_change_cart_item_qty_input(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")

    if message.text.lower() == "/cancel":
        await universal_cancel_message(message, state, user_data)
        return

    new_quantity = validate_qty_util(message.text)
    state_data = await state.get_data()
    product_id = state_data.get("editing_cart_product_id")
    location_id = state_data.get("editing_cart_location_id")
    product_name = state_data.get("editing_cart_product_name", get_text("unknown_product", language)) # New locale
    current_qty = state_data.get("editing_cart_current_qty", 0)
    max_stock = state_data.get("editing_cart_max_stock", 0)

    if not all([product_id, location_id]): # Check if essential data is present
        await message.answer(get_text("error_occurred", language))
        return await _go_to_main_menu(message, state, user_data)

    if new_quantity is None: 
        # Re-prompt with error message and keyboard
        prompt_text = get_text("cart_change_item_qty_prompt", language).format(product_name=product_name, current_qty=current_qty)
        error_msg = get_text("invalid_quantity", language)
        cancel_text = get_text("cancel_prompt", language)
        full_prompt = f"{hbold(error_msg)}\n{prompt_text}\n\n{hitalic(cancel_text)}"
        
        await message.answer(
             full_prompt,
             reply_markup=create_change_cart_item_quantity_keyboard(product_id, location_id, current_qty, max_stock, language),
             parse_mode="HTML"
        )
        return 

    order_service = OrderService()
    success, msg_key_or_error = await order_service.update_cart_item_quantity(message.from_user.id, product_id, location_id, new_quantity, language) 
    
    response_text = get_text(msg_key_or_error, language) if success else msg_key_or_error
    await message.answer(response_text)

    # After update, go back to manage_cart_items view
    cart_items = await order_service.get_cart_contents(message.from_user.id, language) 
    if not cart_items:
        await state.set_state(OrderStates.viewing_cart) # Set state for _display_cart
        return await _display_cart(message, state, user_data) 

    await state.set_state(OrderStates.managing_cart_items)
    await message.answer(
        get_text("manage_cart_items_title", language),
        reply_markup=create_manage_cart_items_keyboard(cart_items, language) 
    )


@router.callback_query(StateFilter(OrderStates.editing_cart_item_quantity), F.data.startswith("process_cart_qty_change:"))
async def process_change_cart_item_qty_callback(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    parts = callback.data.split(":")
    try:
        product_id = int(parts[1])
        location_id = int(parts[2])
        qty_str = parts[3]
        
        if qty_str == "custom":
             state_data = await state.get_data()
             product_name = state_data.get("editing_cart_product_name", get_text("unknown_product", language))
             current_qty = state_data.get("editing_cart_current_qty", 0)
             prompt_text = get_text("cart_change_item_qty_prompt", language).format(product_name=product_name, current_qty=current_qty)
             custom_entry_prompt = get_text("enter_custom_quantity", language)
             cancel_text = get_text("cancel_prompt", language)
             full_prompt = f"{prompt_text}\n\n{hbold(custom_entry_prompt)}\n\n{hitalic(cancel_text)}"
             await callback.message.edit_text(full_prompt, parse_mode="HTML") # Keyboard removed, wait for text
             await callback.answer()
             return 

        new_quantity = int(qty_str)
    except (ValueError, IndexError):
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        return

    order_service = OrderService()
    success, msg_key_or_error = await order_service.update_cart_item_quantity(callback.from_user.id, product_id, location_id, new_quantity, language) 
    
    response_text = get_text(msg_key_or_error, language) if success else msg_key_or_error
    await callback.answer(response_text, show_alert=not success) # Show alert on error

    # After update, go back to manage_cart_items view
    cart_items = await order_service.get_cart_contents(callback.from_user.id, language) 
    if not cart_items: # If cart becomes empty
        await state.set_state(OrderStates.viewing_cart)
        return await _display_cart(callback, state, user_data) 

    await state.set_state(OrderStates.managing_cart_items)
    await callback.message.edit_text(
        get_text("manage_cart_items_title", language),
        reply_markup=create_manage_cart_items_keyboard(cart_items, language) 
    )

# --- Checkout Flow ---
@router.callback_query(StateFilter(OrderStates.viewing_cart), F.data == "checkout")
async def checkout_start_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    order_service = OrderService()
    cart_items = await order_service.get_cart_contents(callback.from_user.id, language) 
    if not cart_items:
        await callback.answer(get_text("cart_empty_checkout", language), show_alert=True)
        return 

    await state.set_state(OrderStates.choosing_payment)
    await callback.message.edit_text(
        get_text("choose_payment_method", language),
        reply_markup=create_payment_methods_keyboard(language, back_callback="view_cart") 
    )
    await callback.answer()

@router.callback_query(StateFilter(OrderStates.choosing_payment), F.data.startswith("payment:"))
async def payment_selected_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    payment_method_code = callback.data.split(":")[1] # e.g. "cash"
    await state.update_data(payment_method=payment_method_code)

    order_service = OrderService()
    cart_items = await order_service.get_cart_contents(callback.from_user.id, language) 
    if not cart_items: 
        await callback.answer(get_text("cart_empty_checkout", language), show_alert=True)
        return await _display_cart(callback, state, user_data)

    summary_text = hbold(get_text("order_confirmation", language)) + "\n\n"
    total_cart_value = Decimal('0')
    for item in cart_items: # item name, variation, location_name already localized
        item_total = item["price"] * item["quantity"]
        total_cart_value += item_total
        summary_text += get_text("cart_item_format_user", language).format(
            name=item["name"], variation=f" ({item['variation']})" if item.get("variation") else "",
            quantity=item["quantity"], price_each=format_price(item["price"]),
            price_total=format_price(item_total), location=item["location_name"]
        ) + "\n\n"
    
    payment_method_display = get_text(f"payment_{payment_method_code}", language) # Get localized payment method name
    summary_text += f"\n{hbold(get_text('payment_method', language))}: {payment_method_display}\n" 
    summary_text += get_text("cart_total", language).format(total=format_price(total_cart_value))
    
    await state.set_state(OrderStates.confirming_order)
    await callback.message.edit_text(
        summary_text,
        reply_markup=create_confirm_order_keyboard(language, back_callback="checkout"), 
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(StateFilter(OrderStates.confirming_order), F.data == "confirm_order")
async def confirm_order_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    state_data = await state.get_data()
    payment_method = state_data.get("payment_method")

    if not payment_method:
        await callback.answer(get_text("error_occurred", language), show_alert=True)
        return await _go_to_main_menu(callback, state, user_data)

    order_service = OrderService()
    order_id, msg_key_or_error = await order_service.create_order_from_cart(callback.from_user.id, payment_method, language=language) 

    final_text = get_text(msg_key_or_error, language) if order_id else msg_key_or_error 
    if order_id : final_text = final_text.format(order_id=order_id) 

    if order_id:
        await callback.answer(get_text("order_confirmed", language), show_alert=False) # Subtle confirmation
    else:
        await callback.answer(get_text("order_creation_failed", language), show_alert=True)

    await state.clear() # Clear FSM state after order attempt
    await callback.message.edit_text(final_text, reply_markup=create_main_menu_keyboard(language), parse_mode="HTML")


@router.callback_query(StateFilter(OrderStates.confirming_order), F.data == "cancel_order_confirmation") 
async def cancel_order_from_confirmation_handler(callback: types.CallbackQuery, state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    await callback.answer(get_text("order_cancelled_alert", language), show_alert=True)
    # Go back to cart view, not main menu directly
    await _display_cart(callback, state, user_data)


# --- Order History ---
@router.message(Command("orders"), StateFilter("*")) # Allow from any state
@router.callback_query(F.data == "my_orders", StateFilter("*"))
async def my_orders_handler(event: Union[types.Message, types.CallbackQuery], state: FSMContext, user_data: Dict[str, Any]):
    language = user_data.get("language", "en")
    user_id = user_data.get("user_id")
    order_service = OrderService()
    
    # For now, show last 5. Pagination can be added using create_paginated_keyboard.
    orders = await order_service.get_user_orders_formatted(user_id, language, limit=5) 

    if not orders:
        text = get_text("no_orders_found", language)
    else:
        text = hbold(get_text("your_orders", language)) + "\n\n"
        for order_detail in orders: # OrderService provides localized status_display and formatted dates/prices
            text += get_text("order_item_user_format", language).format( 
                id=order_detail["id"],
                date=order_detail["created_at_display"],
                status_emoji=order_detail["status_emoji"],
                status=order_detail["status_display"],
                total=order_detail["total_amount_display"]
            ) + "\n\n" # Double newline for spacing
    
    current_fsm_state = await state.get_state()
    if current_fsm_state is not None: # If user was in a state, clear it
        await state.clear()
        # Optionally notify user that previous action was cancelled
        if isinstance(event, types.Message): # Only if invoked by command while in FSM
            await event.answer(get_text("action_cancelled", language), parse_mode="HTML")


    kb = create_back_to_menu_keyboard(language) 
    if isinstance(event, types.Message):
        await event.answer(text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception: # If edit fails
            await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()

# --- Universal Cancel and Back to Main Menu ---
@router.message(Command("cancel"), StateFilter("*")) # Handles /cancel from any state
async def universal_cancel_message(message: types.Message, state: FSMContext, user_data: Dict[str, Any]):
    current_fsm_state_str = await state.get_state()
    language = user_data.get("language", "en")
    
    if current_fsm_state_str is not None:
        logger.info(f"User {message.from_user.id} cancelled FSM state {current_fsm_state_str} via /cancel command.")
        
        # Check if the state belongs to Admin FSMs
        # Assuming Admin state names start with "Admin" (e.g., "AdminOrderManagementStates:VIEWING_ORDERS_LIST")
        if current_fsm_state_str.startswith("Admin"): # Basic check
             from app.handlers.admin_handlers import admin_panel_command # Local import to avoid circularity at top level
             await state.clear()
             await message.answer(get_text("admin_action_cancelled", language))
             # Create a mock user_data for admin_panel_command if it needs more than lang
             admin_user_data = {"language": language, "user_id": message.from_user.id}
             await admin_panel_command(message, state, admin_user_data) # Redirect to admin panel
             return

        # Default behavior for non-admin states: clear state and go to main menu
        await message.answer(get_text("action_cancelled", language))
    
    # If no state or after clearing non-admin state, go to main menu
    await _go_to_main_menu(message, state, user_data)


# Need a get_cart_item_details in OrderService for `change_specific_cart_item_qty_prompt`
# It should fetch a single cart item with its details (qty, product name, stock)

# New locales used:
# "unknown_product": {"en": "Unknown Product", "ru": "Неизвестный товар", "pl": "Nieznany produkt"},





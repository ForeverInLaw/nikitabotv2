"""
Order service for managing order-related business logic.
Handles cart operations, order creation, status management, and stock coordination.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from app.db.database import get_session
from app.db.repositories.order_repo import OrderRepository
from app.db.repositories.product_repo import ProductRepository
from app.db.models import Order, OrderItem, UserCart
from app.localization.locales import get_text
from app.utils.helpers import (
    OrderStatusEnum, format_price, format_datetime, 
    get_order_status_emoji, get_payment_method_emoji
)
from app.services.product_service import ProductService

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order and cart management operations."""

    async def get_cart_contents(self, user_id: int, language: str = "en") -> List[Dict[str, Any]]:
        """Get formatted cart contents for user display."""
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                cart_items = await order_repo.get_cart_items(user_id)
                
                formatted_items = []
                for item in cart_items:
                    # Get localized product name
                    localized_name = None
                    for loc in item.product.localizations:
                        if loc.language_code == language:
                            localized_name = loc.name
                            break
                    
                    name = localized_name or f"Product {item.product_id}"
                    
                    formatted_items.append({
                        "product_id": item.product_id,
                        "location_id": item.location_id,
                        "name": name,
                        "variation": item.product.variation,
                        "quantity": item.quantity,
                        "price": item.product.cost,
                        "location_name": item.location.name
                    })
                
                return formatted_items
                
        except Exception as e:
            logger.error(f"Error getting cart contents for user {user_id}: {e}", exc_info=True)
            return []

    async def update_cart_item_quantity(
        self, 
        user_id: int, 
        product_id: int, 
        location_id: int, 
        new_quantity: int,
        language: str = "en"
    ) -> Tuple[bool, str]:
        """
        Set cart item to specific quantity.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                product_repo = ProductRepository(session)
                
                # Check stock availability
                stock_record = await product_repo.get_stock_record(product_id, location_id)
                available_stock = stock_record.quantity if stock_record else 0
                
                if new_quantity > available_stock:
                    product = await product_repo.get_product_by_id(product_id)
                    product_name = None
                    if product:
                        for loc in product.localizations:
                            if loc.language_code == language:
                                product_name = loc.name
                                break
                    product_name = product_name or f"Product {product_id}"
                    
                    return False, get_text("quantity_exceeds_stock_at_add", language).format(
                        requested=new_quantity,
                        product_name=product_name,
                        available=available_stock,
                        units_short=get_text("units_short", language)
                    )
                
                await order_repo.add_or_update_cart_item(user_id, product_id, location_id, new_quantity)
                await session.commit()
                
                logger.info(f"Updated cart item for user {user_id}: product {product_id} at location {location_id} to quantity {new_quantity}")
                return True, "cart_item_quantity_updated"
                
        except Exception as e:
            logger.error(f"Error updating cart item quantity: {e}", exc_info=True)
            return False, "failed_to_add_to_cart"

    async def remove_from_cart(
        self, 
        user_id: int, 
        product_id: int, 
        location_id: int,
        language: str = "en"
    ) -> Tuple[bool, str]:
        """
        Remove item from cart.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                
                success = await order_repo.remove_cart_item(user_id, product_id, location_id)
                if success:
                    await session.commit()
                    logger.info(f"Removed cart item for user {user_id}: product {product_id} at location {location_id}")
                    return True, "cart_item_removed"
                else:
                    return False, "cart_item_not_found"
                    
        except Exception as e:
            logger.error(f"Error removing from cart: {e}", exc_info=True)
            return False, "failed_to_add_to_cart"

    async def clear_cart(self, user_id: int) -> bool:
        """Clear all items from user's cart."""
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                await order_repo.clear_cart(user_id)
                await session.commit()
                logger.info(f"Cleared cart for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing cart for user {user_id}: {e}", exc_info=True)
            return False

    async def get_cart_item_details(
        self, 
        user_id: int, 
        product_id: int, 
        location_id: int,
        language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Get details of a specific cart item."""
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                
                cart_item = await order_repo.get_cart_item(user_id, product_id, location_id)
                if not cart_item:
                    return None
                
                return {
                    "product_id": product_id,
                    "location_id": location_id,
                    "quantity": cart_item.quantity
                }
                
        except Exception as e:
            logger.error(f"Error getting cart item details: {e}", exc_info=True)
            return None

    async def create_order_from_cart(
        self, 
        user_id: int, 
        payment_method: str,
        language: str = "en"
    ) -> Tuple[Optional[int], str]:
        """
        Create order from cart contents.
        Returns (order_id, message_key).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                product_repo = ProductRepository(session)
                
                # Get cart items with lock
                cart_items = await order_repo.get_cart_items(user_id, for_update=True)
                if not cart_items:
                    return None, "cart_empty_checkout"
                
                # Validate stock availability for each item
                total_amount = Decimal('0')
                for item in cart_items:
                    stock_record = await product_repo.get_stock_record(
                        item.product_id, item.location_id, for_update=True
                    )
                    available_stock = stock_record.quantity if stock_record else 0
                    
                    if item.quantity > available_stock:
                        # Get localized product name
                        product_name = None
                        for loc in item.product.localizations:
                            if loc.language_code == language:
                                product_name = loc.name
                                break
                        product_name = product_name or f"Product {item.product_id}"
                        
                        await session.rollback()
                        return None, get_text("order_creation_stock_insufficient", language).format(
                            product_name=product_name,
                            available=available_stock,
                            requested=item.quantity,
                            units_short=get_text("units_short", language)
                        )
                    
                    total_amount += item.product.cost * item.quantity
                
                # Create order
                order = Order(
                    user_id=user_id,
                    status=OrderStatusEnum.PENDING_ADMIN_APPROVAL.value,
                    payment_method=payment_method,
                    total_amount=total_amount
                )
                order = await order_repo.create_order(order)
                
                # Create order items and reserve stock
                for item in cart_items:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        location_id=item.location_id,
                        quantity=item.quantity,
                        reserved_quantity=item.quantity,  # Reserve immediately
                        price_at_order=item.product.cost
                    )
                    await order_repo.create_order_item(order_item)
                    
                    # Reserve stock
                    await product_repo.update_stock_quantity(
                        item.product_id, item.location_id, -item.quantity
                    )
                
                # Clear cart
                await order_repo.clear_cart(user_id)
                await session.commit()
                
                logger.info(f"Created order {order.id} for user {user_id} with {len(cart_items)} items")
                return order.id, "order_created_successfully"
                
        except Exception as e:
            logger.error(f"Error creating order from cart for user {user_id}: {e}", exc_info=True)
            return None, "order_creation_failed_db"

    async def get_user_orders_formatted(
        self, 
        user_id: int, 
        language: str = "en",
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get formatted user orders for display."""
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                orders = await order_repo.get_user_orders(user_id, limit, offset)
                
                formatted_orders = []
                for order in orders:
                    status_emoji = get_order_status_emoji(order.status)
                    status_display = get_text(f"order_status_{order.status}", language)
                    
                    formatted_orders.append({
                        "id": order.id,
                        "status_emoji": status_emoji,
                        "status_display": status_display,
                        "total_amount_display": format_price(order.total_amount),
                        "created_at_display": format_datetime(order.created_at, language)
                    })
                
                return formatted_orders
                
        except Exception as e:
            logger.error(f"Error getting formatted orders for user {user_id}: {e}", exc_info=True)
            return []

    async def get_orders_list_for_admin(
        self,
        language: str = "en",
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
        user_id_filter: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get formatted orders list for admin.
        Returns (formatted_orders, total_count).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                
                orders = await order_repo.list_orders(
                    status=status_filter,
                    user_id=user_id_filter,
                    limit=limit,
                    offset=offset
                )
                total_count = await order_repo.count_orders(
                    status=status_filter,
                    user_id=user_id_filter
                )
                
                formatted_orders = []
                for order in orders:
                    status_emoji = get_order_status_emoji(order.status)
                    status_display = get_text(f"order_status_{order.status}", language)
                    user_display = f"User {order.user_id}"
                    
                    formatted_orders.append({
                        "id": order.id,
                        "summary_text": get_text("admin_order_summary_list_format", language).format(
                            status_emoji=status_emoji,
                            id=order.id,
                            user=user_display,
                            total=format_price(order.total_amount),
                            date=format_datetime(order.created_at, language)
                        ),
                        "status_raw": order.status,
                        "user_id": order.user_id,
                        "total_amount": order.total_amount,
                        "created_at": order.created_at
                    })
                
                return formatted_orders, total_count
                
        except Exception as e:
            logger.error(f"Error getting orders list for admin: {e}", exc_info=True)
            return [], 0

    async def get_order_details_for_admin(self, order_id: int, language: str = "en") -> Optional[Dict[str, Any]]:
        """Get detailed order information for admin view."""
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                
                order = await order_repo.get_order_by_id(order_id)
                if not order:
                    return None
                
                # Format order details
                status_emoji = get_order_status_emoji(order.status)
                status_display = get_text(f"order_status_{order.status}", language)
                payment_display = get_text(f"payment_{order.payment_method}", language)
                
                # Format order items
                items_formatted = []
                for item in order.items:
                    # Get localized product name
                    product_name = None
                    for loc in item.product.localizations:
                        if loc.language_code == language:
                            product_name = loc.name
                            break
                    product_name = product_name or f"Product {item.product_id}"
                    
                    item_total = item.price_at_order * item.quantity
                    
                    items_formatted.append({
                        "product_name": product_name,
                        "location_name": item.location.name,
                        "quantity": item.quantity,
                        "reserved_quantity": item.reserved_quantity,
                        "price_at_order_display": format_price(item.price_at_order),
                        "item_total_display": format_price(item_total)
                    })
                
                return {
                    "id": order.id,
                    "user_id": order.user_id,
                    "user_display": f"User {order.user_id}",
                    "status_raw": order.status,
                    "status_emoji": status_emoji,
                    "status_display": status_display,
                    "payment_method_raw": order.payment_method,
                    "payment_method_display": payment_display,
                    "total_amount_display": format_price(order.total_amount),
                    "created_at_display": format_datetime(order.created_at, language),
                    "updated_at_iso": order.updated_at.isoformat() if order.updated_at else None,
                    "admin_notes": order.admin_notes,
                    "items": items_formatted
                }
                
        except Exception as e:
            logger.error(f"Error getting order details for admin {order_id}: {e}", exc_info=True)
            return None

    async def approve_order(self, order_id: int, admin_id: int, language: str = "en") -> Tuple[bool, str]:
        """
        Approve an order by admin.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                
                order = await order_repo.get_order_by_id_for_update(order_id)
                if not order:
                    return False, "admin_order_not_found"
                
                if order.status != OrderStatusEnum.PENDING_ADMIN_APPROVAL.value:
                    return False, "admin_order_already_processed"
                
                await order_repo.update_order_status(
                    order_id, 
                    OrderStatusEnum.APPROVED.value,
                    f"Approved by admin {admin_id}"
                )
                await session.commit()
                
                logger.info(f"Admin {admin_id} approved order {order_id}")
                return True, "admin_order_approved"
                
        except Exception as e:
            logger.error(f"Error approving order {order_id} by admin {admin_id}: {e}", exc_info=True)
            return False, "order_creation_failed_db"

    async def reject_order(self, order_id: int, admin_id: int, reason: str, language: str = "en") -> Tuple[bool, str]:
        """
        Reject an order by admin and release reserved stock.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                product_repo = ProductRepository(session)
                
                order = await order_repo.get_order_by_id_for_update(order_id)
                if not order:
                    return False, "admin_order_not_found"
                
                if order.status != OrderStatusEnum.PENDING_ADMIN_APPROVAL.value:
                    return False, "admin_order_already_processed"
                
                # Release reserved stock
                for item in order.items:
                    if item.reserved_quantity > 0:
                        await product_repo.update_stock_quantity(
                            item.product_id, item.location_id, item.reserved_quantity
                        )
                        await order_repo.update_order_item_reserved_quantity(item.id, 0)
                
                await order_repo.update_order_status(
                    order_id,
                    OrderStatusEnum.REJECTED.value,
                    f"Rejected by admin {admin_id}: {reason}"
                )
                await session.commit()
                
                logger.info(f"Admin {admin_id} rejected order {order_id}")
                return True, "admin_order_rejected"
                
        except Exception as e:
            logger.error(f"Error rejecting order {order_id} by admin {admin_id}: {e}", exc_info=True)
            return False, "order_creation_failed_db"

    async def cancel_order_by_admin(self, order_id: int, admin_id: int, reason: str, language: str = "en") -> Tuple[bool, str]:
        """
        Cancel an order by admin and release stock if applicable.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                order_repo = OrderRepository(session)
                product_repo = ProductRepository(session)
                
                order = await order_repo.get_order_by_id_for_update(order_id)
                if not order:
                    return False, "admin_order_not_found"
                
                # Only allow cancellation for non-final states
                if order.status in [OrderStatusEnum.COMPLETED.value, OrderStatusEnum.CANCELLED.value, OrderStatusEnum.REJECTED.value]:
                    return False, "admin_order_already_processed"
                
                # Release any reserved stock
                for item in order.items:
                    if item.reserved_quantity > 0:
                        await product_repo.update_stock_quantity(
                            item.product_id, item.location_id, item.reserved_quantity
                        )
                        await order_repo.update_order_item_reserved_quantity(item.id, 0)
                
                await order_repo.update_order_status(
                    order_id,
                    OrderStatusEnum.CANCELLED.value,
                    f"Cancelled by admin {admin_id}: {reason}"
                )
                await session.commit()
                
                logger.info(f"Admin {admin_id} cancelled order {order_id}")
                return True, "admin_order_cancelled"
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id} by admin {admin_id}: {e}", exc_info=True)
            return False, "order_creation_failed_db"

    async def change_order_status_by_admin(
        self, 
        order_id: int, 
        new_status: str, 
        admin_id: int,
        notes: Optional[str] = None,
        language: str = "en"
    ) -> Tuple[bool, str]:
        """
        Change order status by admin.
        Returns (success, message_key).
        """
        try:
            if new_status not in OrderStatusEnum.values():
                return False, "admin_invalid_status_transition"
            
            async with get_session() as session:
                order_repo = OrderRepository(session)
                
                order = await order_repo.get_order_by_id_for_update(order_id)
                if not order:
                    return False, "admin_order_not_found"
                
                # Basic validation - prevent changing from final states
                if order.status in [OrderStatusEnum.COMPLETED.value, OrderStatusEnum.CANCELLED.value, OrderStatusEnum.REJECTED.value]:
                    return False, "admin_order_already_processed"
                
                admin_note = f"Status changed by admin {admin_id} from {order.status} to {new_status}"
                if notes:
                    admin_note += f": {notes}"
                
                await order_repo.update_order_status(order_id, new_status, admin_note)
                await session.commit()
                
                logger.info(f"Admin {admin_id} changed order {order_id} status to {new_status}")
                return True, "admin_order_status_updated"
                
        except Exception as e:
            logger.error(f"Error changing order {order_id} status by admin {admin_id}: {e}", exc_info=True)
            return False, "order_creation_failed_db"


"""
Order repository for database operations.
Data access layer for order and cart queries.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, OrderItem, UserCart, Product, Location, ProductLocalization, User
from app.utils.helpers import OrderStatusEnum


logger = logging.getLogger(__name__)


class OrderRepository:
    """Repository for order data access operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID with user, items, item products (with localizations), and item locations."""
        result = await self.session.execute(
            select(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.items)
                .joinedload(OrderItem.product)
                .selectinload(Product.localizations), # Use selectinload for product localizations
                joinedload(Order.items)
                .joinedload(OrderItem.location)
            )
            .where(Order.id == order_id)
        )
        return result.unique().scalar_one_or_none() # unique() due to multiple joinedload paths to items

    async def get_order_by_id_for_update(self, order_id: int) -> Optional[Order]:
        """Get order by ID with items, FOR UPDATE (locks order and items)."""
        result = await self.session.execute(
            select(Order)
            .options(joinedload(Order.items)) # Load items
            .where(Order.id == order_id)
            .with_for_update() # Lock the order and implicitly its items if cascade is set
        )
        # Using unique() as items is a collection
        return result.unique().scalar_one_or_none()

    async def get_user_orders(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Order]:
        """Get all orders for a user, paginated."""
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def count_user_orders(self, user_id: int) -> int:
        """Count total orders for a user."""
        result = await self.session.execute(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        )
        return result.scalar_one()

    async def list_orders(
        self, 
        status: Optional[str] = None, 
        user_id: Optional[int] = None,
        limit: int = 20, 
        offset: int = 0
    ) -> List[Order]:
        """List orders with optional status/user filtering and pagination."""
        stmt = select(Order).options(joinedload(Order.user)).order_by(Order.created_at.desc())
        if status:
            stmt = stmt.where(Order.status == status)
        if user_id:
            stmt = stmt.where(Order.user_id == user_id)
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_orders(self, status: Optional[str] = None, user_id: Optional[int] = None) -> int:
        """Count orders with optional status/user filtering."""
        stmt = select(func.count(Order.id))
        if status:
            stmt = stmt.where(Order.status == status)
        if user_id:
            stmt = stmt.where(Order.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
        
    async def create_order(self, order: Order) -> Order:
        """Create new order."""
        self.session.add(order)
        await self.session.flush() # Flush to get ID and defaults before returning
        await self.session.refresh(order) # Ensure all attributes are loaded
        return order

    async def create_order_item(self, order_item: OrderItem) -> OrderItem:
        """Create a new order item."""
        self.session.add(order_item)
        await self.session.flush()
        await self.session.refresh(order_item)
        return order_item
        
    async def update_order_status(self, order_id: int, status: str, admin_notes: Optional[str] = None) -> Optional[Order]:
        """Update the status of an order and optionally admin notes."""
        order = await self.get_order_by_id(order_id) # Fetch with relations if needed by caller
        if order:
            order.status = status
            if admin_notes is not None:
                 order.admin_notes = admin_notes
            await self.session.flush()
            await self.session.refresh(order)
            return order
        return None

    async def update_order_item_reserved_quantity(self, item_id: int, reserved_quantity: int) -> Optional[OrderItem]:
        """Update the reserved quantity of an order item."""
        item = await self.session.get(OrderItem, item_id)
        if item:
            item.reserved_quantity = reserved_quantity
            await self.session.flush()
            await self.session.refresh(item)
            return item
        return None

    # --- Cart Methods ---
    async def get_cart_item(self, user_id: int, product_id: int, location_id: int) -> Optional[UserCart]:
        """Get a specific item from user's cart."""
        result = await self.session.execute(
            select(UserCart)
            .where(
                UserCart.user_id == user_id,
                UserCart.product_id == product_id,
                UserCart.location_id == location_id
            )
        )
        return result.scalar_one_or_none()

    async def get_cart_items(self, user_id: int, for_update: bool = False) -> List[UserCart]:
        """Get user's cart items with product, localizations, and location details."""
        stmt = (
            select(UserCart)
            .options(
                joinedload(UserCart.product)
                .selectinload(Product.localizations), # Use selectinload for product localizations
                joinedload(UserCart.location)
            )
            .where(UserCart.user_id == user_id)
        )
        if for_update:
            stmt = stmt.with_for_update() # Lock cart items

        result = await self.session.execute(stmt)
        return result.unique().scalars().all() # unique() due to multiple join paths

    async def add_or_update_cart_item(self, user_id: int, product_id: int, location_id: int, quantity: int) -> UserCart:
        """Add a new item to cart or update quantity if it exists."""
        cart_item = await self.get_cart_item(user_id, product_id, location_id)
        if cart_item:
            cart_item.quantity = quantity
        else:
            cart_item = UserCart(
                user_id=user_id,
                product_id=product_id,
                location_id=location_id,
                quantity=quantity
            )
            self.session.add(cart_item)
        await self.session.flush()
        await self.session.refresh(cart_item)
        return cart_item

    async def remove_cart_item(self, user_id: int, product_id: int, location_id: int) -> bool:
        """Remove a specific item from user's cart."""
        cart_item = await self.get_cart_item(user_id, product_id, location_id)
        if cart_item:
            await self.session.delete(cart_item)
            await self.session.flush()
            return True
        return False

    async def clear_cart(self, user_id: int):
        """Clear all items from user's cart."""
        await self.session.execute(
            delete(UserCart).where(UserCart.user_id == user_id)
        )
        await self.session.flush()






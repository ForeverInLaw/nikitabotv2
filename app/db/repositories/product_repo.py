"""
Product repository for database operations.
Data access layer for product and inventory queries.
Handles CRUD operations for products, categories, manufacturers, and stock.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy import select, insert, update, delete, func
import sqlalchemy as sa # Added import
from sqlalchemy.orm import joinedload, selectinload # selectinload was already here, but explicitly mentioned
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError


from app.db.models import Product, ProductLocalization, ProductStock, Location, Manufacturer, Category, Base # Product, Category, Manufacturer, Location, ProductLocalization were already here

logger = logging.getLogger(__name__)


class ProductRepository:
    """Repository for product data access operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Product Methods ---
    async def create_product(
        self, 
        manufacturer_id: int, 
        cost: Decimal, 
        category_id: Optional[int] = None,
        sku: Optional[str] = None, 
        image_url: Optional[str] = None, 
        variation: Optional[str] = None
    ) -> Product:
        """Create a new product."""
        product = Product(
            manufacturer_id=manufacturer_id,
            category_id=category_id,
            cost=cost,
            sku=sku,
            image_url=image_url,
            variation=variation
        )
        self.session.add(product)
        await self.session.flush() 
        return product

    async def get_product_by_id(self, product_id: int, with_details: bool = True) -> Optional[Product]:
        """Get product by ID with optional localizations, manufacturer, category, and stock."""
        stmt = select(Product).where(Product.id == product_id)
        if with_details:
            stmt = stmt.options(
                selectinload(Product.localizations), # Use selectinload for collections
                joinedload(Product.manufacturer),
                joinedload(Product.category),
                selectinload(Product.stocks).joinedload(ProductStock.location) # Load stock and their locations
            )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none() # unique() for selectinload

    async def list_products(self, limit: int = 100, offset: int = 0, with_details: bool = True) -> List[Product]:
        """List all products with optional details."""
        stmt = select(Product).limit(limit).offset(offset).order_by(Product.id)
        if with_details:
            stmt = stmt.options(
                selectinload(Product.localizations),
                joinedload(Product.manufacturer),
                joinedload(Product.category)
            )
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    async def update_product(self, product_id: int, **updates: Any) -> Optional[Product]:
        """Update product details."""
        # Ensure 'cost' is Decimal if present
        if 'cost' in updates and updates['cost'] is not None:
            updates['cost'] = Decimal(str(updates['cost']))

        await self.session.execute(
            update(Product).where(Product.id == product_id).values(**updates)
        )
        # No commit here, service layer handles transaction
        return await self.get_product_by_id(product_id, with_details=False) # Fetch updated product, no need for full details here

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product by ID. Returns True if deletion successful, False otherwise."""
        # Check for related order items first to prevent deletion if product is in orders
        # This check should ideally be in the service layer for business logic.
        # However, for safety, a basic check can be here or rely on DB constraints.
        # Assuming ondelete="RESTRICT" for OrderItem.product_id handles this at DB level.
        try:
            result = await self.session.execute(
                delete(Product).where(Product.id == product_id)
            )
            # No commit here
            return result.rowcount > 0
        except IntegrityError: # Catches FK violations if product is in an order
            await self.session.rollback() # Rollback this failed attempt
            logger.warning(f"Failed to delete product {product_id} due to existing references (e.g., in orders).")
            return False


    # --- Product Localization Methods ---
    async def add_or_update_product_localization(self, product_id: int, language_code: str, name: str, description: Optional[str] = None) -> ProductLocalization:
        """Add or update product localization."""
        stmt = select(ProductLocalization).where(
            ProductLocalization.product_id == product_id,
            ProductLocalization.language_code == language_code
        )
        result = await self.session.execute(stmt)
        localization = result.scalar_one_or_none()

        if localization:
            localization.name = name
            localization.description = description
        else:
            localization = ProductLocalization(
                product_id=product_id,
                language_code=language_code,
                name=name,
                description=description
            )
            self.session.add(localization)
        await self.session.flush()
        return localization

    async def get_product_localizations(self, product_id: int) -> List[ProductLocalization]:
        """Get all localizations for a product."""
        result = await self.session.execute(
            select(ProductLocalization).where(ProductLocalization.product_id == product_id)
        )
        return result.scalars().all()

    async def get_product_localization(self, product_id: int, language_code: str) -> Optional[ProductLocalization]:
        """Get specific product localization."""
        result = await self.session.execute(
            select(ProductLocalization)
            .where(ProductLocalization.product_id == product_id)
            .where(ProductLocalization.language_code == language_code)
        )
        return result.scalar_one_or_none()

    # --- Stock Management Methods ---
    async def get_stock_record(self, product_id: int, location_id: int, for_update: bool = False) -> Optional[ProductStock]:
        """Get a specific stock record, optionally locking for updates."""
        stmt = select(ProductStock).where(
            ProductStock.product_id == product_id,
            ProductStock.location_id == location_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_stock_quantity(self, product_id: int, location_id: int, quantity_change: int) -> Optional[ProductStock]:
        """
        Update stock quantity for a product at a location by a delta.
        Returns the updated ProductStock record or None on failure (e.g., insufficient stock).
        This method expects the service layer to handle overall transaction commit/rollback.
        """
        stock = await self.get_stock_record(product_id, location_id, for_update=True)

        if stock:
            new_quantity = stock.quantity + quantity_change
            if new_quantity < 0:
                logger.warning(f"Attempt to set stock for P:{product_id} L:{location_id} to {new_quantity}, which is negative. Operation aborted.")
                # No rollback here, let service layer decide. Return None to indicate failure.
                return None 
            stock.quantity = new_quantity
        else:
            if quantity_change < 0:
                logger.warning(f"Attempt to decrease stock for non-existent record P:{product_id} L:{location_id}. Operation aborted.")
                return None # Cannot decrease stock for a non-existent record
            # Create new stock record if it doesn't exist and quantity_change is positive
            stock = ProductStock(
                product_id=product_id,
                location_id=location_id,
                quantity=quantity_change # Initial quantity is the positive change
            )
            self.session.add(stock)
        
        await self.session.flush() # Flush to apply changes within current transaction
        await self.session.refresh(stock) # Refresh to get updated state
        return stock
        
    async def set_stock_quantity(self, product_id: int, location_id: int, new_absolute_quantity: int) -> Optional[ProductStock]:
        """Sets the stock quantity for a product at a location to an absolute value."""
        if new_absolute_quantity < 0:
            logger.warning(f"Attempt to set stock for P:{product_id} L:{location_id} to {new_absolute_quantity} (negative). Operation aborted.")
            return None

        stock = await self.get_stock_record(product_id, location_id, for_update=True)
        if stock:
            stock.quantity = new_absolute_quantity
        else:
            stock = ProductStock(
                product_id=product_id,
                location_id=location_id,
                quantity=new_absolute_quantity
            )
            self.session.add(stock)
        await self.session.flush()
        await self.session.refresh(stock)
        return stock

    async def get_product_stocks(self, product_id: int) -> List[ProductStock]:
        """Get all stock records for a given product, with location details."""
        result = await self.session.execute(
            select(ProductStock)
            .options(joinedload(ProductStock.location))
            .where(ProductStock.product_id == product_id)
        )
        return result.scalars().all()


    # --- Category Methods ---
    async def create_category(self, name: str) -> Category:
        """Create a new category."""
        category = Category(name=name)
        self.session.add(category)
        await self.session.flush()
        return category

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_category_by_name(self, name: str) -> Optional[Category]:
        """Get category by name."""
        result = await self.session.execute(
            select(Category).where(func.lower(Category.name) == func.lower(name))
        )
        return result.scalar_one_or_none()

    async def list_categories(self, limit: int = 100, offset: int = 0) -> List[Category]:
        """List all categories."""
        result = await self.session.execute(
            select(Category).limit(limit).offset(offset).order_by(Category.name)
        )
        return result.scalars().all()

    async def update_category(self, category_id: int, name: str) -> Optional[Category]:
        """Update category name."""
        category = await self.get_category_by_id(category_id)
        if category:
            category.name = name
            await self.session.flush()
            return category
        return None

    async def delete_category(self, category_id: int) -> bool:
        """Delete a category by ID. Returns True if deletion successful."""
        # Check if category is in use by products
        product_count_stmt = select(func.count(Product.id)).where(Product.category_id == category_id)
        product_count = await self.session.scalar(product_count_stmt)
        if product_count > 0:
            logger.warning(f"Attempt to delete category {category_id} which is used by {product_count} products.")
            return False # Prevent deletion if category is in use

        result = await self.session.execute(
            delete(Category).where(Category.id == category_id)
        )
        return result.rowcount > 0

    # --- Manufacturer Methods ---
    async def create_manufacturer(self, name: str) -> Manufacturer:
        """Create a new manufacturer."""
        manufacturer = Manufacturer(name=name)
        self.session.add(manufacturer)
        await self.session.flush()
        return manufacturer

    async def get_manufacturer_by_id(self, manufacturer_id: int) -> Optional[Manufacturer]:
        """Get manufacturer by ID."""
        result = await self.session.execute(
            select(Manufacturer).where(Manufacturer.id == manufacturer_id)
        )
        return result.scalar_one_or_none()
        
    async def get_manufacturer_by_name(self, name: str) -> Optional[Manufacturer]:
        """Get manufacturer by name."""
        result = await self.session.execute(
            select(Manufacturer).where(func.lower(Manufacturer.name) == func.lower(name))
        )
        return result.scalar_one_or_none()

    async def list_manufacturers(self, limit: int = 100, offset: int = 0) -> List[Manufacturer]:
        """List all manufacturers."""
        result = await self.session.execute(
            select(Manufacturer).limit(limit).offset(offset).order_by(Manufacturer.name)
        )
        return result.scalars().all()

    async def update_manufacturer(self, manufacturer_id: int, name: str) -> Optional[Manufacturer]:
        """Update manufacturer name."""
        manufacturer = await self.get_manufacturer_by_id(manufacturer_id)
        if manufacturer:
            manufacturer.name = name
            await self.session.flush()
            return manufacturer
        return None

    async def delete_manufacturer(self, manufacturer_id: int) -> bool:
        """Delete a manufacturer by ID. Returns True if deletion successful."""
        # Check if manufacturer is in use by products
        product_count_stmt = select(func.count(Product.id)).where(Product.manufacturer_id == manufacturer_id)
        product_count = await self.session.scalar(product_count_stmt)
        if product_count > 0:
            logger.warning(f"Attempt to delete manufacturer {manufacturer_id} which is used by {product_count} products.")
            return False # Prevent deletion

        result = await self.session.execute(
            delete(Manufacturer).where(Manufacturer.id == manufacturer_id)
        )
        return result.rowcount > 0

    # --- Location Methods ---
    async def create_location(self, name: str, address: Optional[str] = None) -> Location:
        """Create a new location."""
        location = Location(name=name, address=address)
        self.session.add(location)
        await self.session.flush()
        return location

    async def get_location_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        result = await self.session.execute(
            select(Location).where(Location.id == location_id)
        )
        return result.scalar_one_or_none()

    async def get_location_by_name(self, name: str) -> Optional[Location]:
        """Get location by name."""
        result = await self.session.execute(
            select(Location).where(func.lower(Location.name) == func.lower(name))
        )
        return result.scalar_one_or_none()

    async def list_locations(self, limit: int = 100, offset: int = 0) -> List[Location]:
        """List all locations."""
        result = await self.session.execute(
            select(Location).limit(limit).offset(offset).order_by(Location.name)
        )
        return result.scalars().all()

    async def update_location(self, location_id: int, name: Optional[str] = None, address: Optional[str] = None) -> Optional[Location]:
        """Update location details."""
        location = await self.get_location_by_id(location_id)
        if location:
            if name is not None:
                location.name = name
            if address is not None: # Allow setting address to empty string
                location.address = address
            await self.session.flush()
            return location
        return None

    async def delete_location(self, location_id: int) -> bool:
        """Delete a location by ID. Returns True if deletion successful."""
        # Check if location is in use by product_stock or order_items
        stock_count_stmt = select(func.count(ProductStock.product_id)).where(ProductStock.location_id == location_id)
        stock_count = await self.session.scalar(stock_count_stmt)
        if stock_count > 0:
            logger.warning(f"Attempt to delete location {location_id} which has {stock_count} stock records.")
            return False # Prevent deletion

        # Add similar check for order_items if necessary, though ondelete="RESTRICT" should handle it.

        result = await self.session.execute(
            delete(Location).where(Location.id == location_id)
        )
        return result.rowcount > 0

    # --- User-facing read methods (from original structure) ---
    async def get_locations_with_stock(self) -> List[Location]:
        """Get locations that have products in stock."""
        result = await self.session.execute(
            select(Location)
            .join(ProductStock)
            .where(ProductStock.quantity > 0)
            .distinct()
            .order_by(Location.name)
        )
        return result.scalars().all()

    async def get_manufacturers_by_location(self, location_id: int) -> List[Manufacturer]:
        """Get manufacturers with products at location."""
        result = await self.session.execute(
            select(Manufacturer)
            .join(Product)
            .join(ProductStock)
            .where(ProductStock.location_id == location_id)
            .where(ProductStock.quantity > 0)
            .distinct()
            .order_by(Manufacturer.name)
        )
        return result.scalars().all()

    async def get_products_by_manufacturer_location(
        self, manufacturer_id: int, location_id: int
    ) -> List[Product]:
        """
        Retrieves products from a specific manufacturer that are in stock at a given location.
        
        Args:
            manufacturer_id: The ID of the manufacturer.
            location_id: The ID of the location.
        
        Returns:
            A list of products from the specified manufacturer available at the given location, including their localizations.
        """
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.localizations))
            .join(ProductStock)
            .where(Product.manufacturer_id == manufacturer_id)
            .where(ProductStock.location_id == location_id)
            .where(ProductStock.quantity > 0)
            .order_by(Product.id) # Or by localized name if complex query is built
        )
        return result.unique().scalars().all()

    async def get_all_products_paginated(self, offset: int, limit: int) -> Tuple[List[Product], int]:
        # Query to fetch products with their localizations
        """
        Retrieves a paginated list of products with their localizations and the total product count.
        
        Args:
            offset: The number of products to skip before starting to collect the result set.
            limit: The maximum number of products to return.
        
        Returns:
            A tuple containing a list of products (each with localizations loaded) and the total number of products in the database.
        """
        stmt = (
            sa.select(Product)
            .options(selectinload(Product.localizations))
            .order_by(Product.id)
            .offset(offset)
            .limit(limit)
        )
        products = await self.session.execute(stmt)
        products_list = list(products.scalars().unique().all()) # Use unique() to avoid duplicates due to join

        # Query to count total products
        total_stmt = sa.select(sa.func.count(Product.id))
        total_products = await self.session.execute(total_stmt)
        total = total_products.scalar_one()
        
        return products_list, total

    async def get_all_categories_paginated(self, offset: int, limit: int) -> Tuple[List[Category], int]:
        """
        Retrieves a paginated list of categories and the total number of categories.
        
        Args:
            offset: The number of categories to skip before starting to collect the result set.
            limit: The maximum number of categories to return.
        
        Returns:
            A tuple containing a list of categories for the current page and the total count of categories.
        """
        stmt = sa.select(Category).order_by(Category.id).offset(offset).limit(limit)
        categories = await self.session.execute(stmt)
        
        total_stmt = sa.select(sa.func.count(Category.id))
        total_categories = await self.session.execute(total_stmt)
        
        return list(categories.scalars().all()), total_categories.scalar_one()

    async def get_all_manufacturers_paginated(self, offset: int, limit: int) -> Tuple[List[Manufacturer], int]:
        """
        Retrieves a paginated list of manufacturers and the total manufacturer count.
        
        Args:
            offset: The number of manufacturers to skip before starting to collect the result set.
            limit: The maximum number of manufacturers to return.
        
        Returns:
            A tuple containing a list of manufacturers for the current page and the total number of manufacturers.
        """
        stmt = sa.select(Manufacturer).order_by(Manufacturer.id).offset(offset).limit(limit)
        manufacturers = await self.session.execute(stmt)
        
        total_stmt = sa.select(sa.func.count(Manufacturer.id))
        total_manufacturers = await self.session.execute(total_stmt)
        
        return list(manufacturers.scalars().all()), total_manufacturers.scalar_one()

    async def get_all_locations_paginated(self, offset: int, limit: int) -> Tuple[List[Location], int]:
        """
        Retrieves a paginated list of locations and the total count of locations.
        
        Args:
            offset: The number of locations to skip before starting to collect the result set.
            limit: The maximum number of locations to return.
        
        Returns:
            A tuple containing a list of locations for the current page and the total number of locations.
        """
        stmt = sa.select(Location).order_by(Location.id).offset(offset).limit(limit)
        locations = await self.session.execute(stmt)
        
        total_stmt = sa.select(sa.func.count(Location.id))
        total_locations = await self.session.execute(total_stmt)
        
        return list(locations.scalars().all()), total_locations.scalar_one()

    async def get_all_locations_for_product_stock(self, offset: int, limit: int) -> Tuple[List[Location], int]:
        # This is similar to get_all_locations_paginated for now
        # Future enhancements could filter locations relevant to a specific product
        """
        Retrieves a paginated list of locations and the total count for product stock management.
        
        Currently returns all locations with pagination; future enhancements may filter by product relevance.
        
        Args:
            offset: The number of records to skip.
            limit: The maximum number of records to return.
        
        Returns:
            A tuple containing a list of locations and the total number of locations.
        """
        stmt = sa.select(Location).order_by(Location.id).offset(offset).limit(limit)
        locations = await self.session.execute(stmt)
        
        total_stmt = sa.select(sa.func.count(Location.id))
        total_locations = await self.session.execute(total_stmt)
        
        return list(locations.scalars().all()), total_locations.scalar_one()
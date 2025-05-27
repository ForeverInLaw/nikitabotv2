"""
Product service for managing product-related business logic.
Handles product CRUD, localization, stock management, and location/manufacturer operations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from app.db.database import get_session
from app.db.repositories.product_repo import ProductRepository
from app.db.models import Product, Location, Manufacturer, Category
from app.localization.locales import get_text
from app.utils.helpers import format_price

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product management operations."""

    async def get_locations_with_stock(self, language: str = "en") -> List[Dict[str, Any]]:
        """Get all locations that have products in stock."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                locations = await product_repo.get_locations_with_stock()
                
                return [{"id": loc.id, "name": loc.name} for loc in locations]
                
        except Exception as e:
            logger.error(f"Error getting locations with stock: {e}", exc_info=True)
            return []

    async def get_manufacturers_by_location(self, location_id: int, language: str = "en") -> List[Dict[str, Any]]:
        """Get manufacturers that have products at a specific location."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                manufacturers = await product_repo.get_manufacturers_by_location(location_id)
                
                return [{"id": mfg.id, "name": mfg.name} for mfg in manufacturers]
                
        except Exception as e:
            logger.error(f"Error getting manufacturers for location {location_id}: {e}", exc_info=True)
            return []

    async def get_products_by_manufacturer_and_location(
        self, 
        manufacturer_id: int, 
        location_id: int, 
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """Get products from a manufacturer at a specific location with localized names."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                products = await product_repo.get_products_by_manufacturer_location(manufacturer_id, location_id)
                
                formatted_products = []
                for product in products:
                    # Get localized name
                    localized_name = None
                    for loc in product.localizations:
                        if loc.language_code == language:
                            localized_name = loc.name
                            break
                    
                    name = localized_name or f"Product {product.id}"
                    
                    formatted_products.append({
                        "id": product.id,
                        "name": name,
                        "variation": product.variation,
                        "price": product.cost
                    })
                
                return formatted_products
                
        except Exception as e:
            logger.error(f"Error getting products for manufacturer {manufacturer_id} at location {location_id}: {e}", exc_info=True)
            return []

    async def get_product_details(self, product_id: int, location_id: int, language: str = "en") -> Optional[Dict[str, Any]]:
        """Get detailed product information including stock at location."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                product = await product_repo.get_product_by_id(product_id)
                if not product:
                    return None
                
                # Get stock for this location
                stock_record = await product_repo.get_stock_record(product_id, location_id)
                stock_quantity = stock_record.quantity if stock_record else 0
                
                # Get localized name and description
                localized_name = None
                localized_description = None
                for loc in product.localizations:
                    if loc.language_code == language:
                        localized_name = loc.name
                        localized_description = loc.description
                        break
                
                name = localized_name or f"Product {product.id}"
                description = localized_description or ""
                
                return {
                    "id": product.id,
                    "name": name,
                    "description": description,
                    "price": product.cost,
                    "stock": stock_quantity,
                    "variation": product.variation,
                    "image_url": product.image_url
                }
                
        except Exception as e:
            logger.error(f"Error getting product details for {product_id} at location {location_id}: {e}", exc_info=True)
            return None

    async def get_location_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                return await product_repo.get_location_by_id(location_id)
        except Exception as e:
            logger.error(f"Error getting location {location_id}: {e}", exc_info=True)
            return None

    async def get_manufacturer_by_id(self, manufacturer_id: int) -> Optional[Manufacturer]:
        """Get manufacturer by ID."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                return await product_repo.get_manufacturer_by_id(manufacturer_id)
        except Exception as e:
            logger.error(f"Error getting manufacturer {manufacturer_id}: {e}", exc_info=True)
            return None

    async def update_stock(self, product_id: int, location_id: int, quantity_change: int, admin_id: int) -> Tuple[bool, str]:
        """
        Update stock quantity (add or subtract).
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                updated_stock = await product_repo.update_stock_quantity(product_id, location_id, quantity_change)
                if updated_stock:
                    await session.commit()
                    logger.info(f"Admin {admin_id} updated stock for product {product_id} at location {location_id} by {quantity_change}")
                    return True, "admin_stock_updated_success"
                else:
                    await session.rollback()
                    return False, "admin_stock_update_failed_insufficient"
                    
        except Exception as e:
            logger.error(f"Error updating stock for product {product_id} at location {location_id}: {e}", exc_info=True)
            return False, "admin_stock_update_failed_db"

    async def get_stock_info(self, product_id: int, location_id: int) -> Optional[Dict[str, Any]]:
        """Get current stock information for a product at location."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                stock_record = await product_repo.get_stock_record(product_id, location_id)
                if stock_record:
                    return {
                        "product_id": product_id,
                        "location_id": location_id,
                        "quantity": stock_record.quantity
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting stock info for product {product_id} at location {location_id}: {e}", exc_info=True)
            return None

    async def reserve_stock(self, product_id: int, location_id: int, quantity: int) -> bool:
        """
        Reserve stock for an order (decrease available stock).
        Used internally by OrderService during order creation.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                updated_stock = await product_repo.update_stock_quantity(product_id, location_id, -quantity)
                if updated_stock:
                    await session.commit()
                    logger.info(f"Reserved {quantity} units of product {product_id} at location {location_id}")
                    return True
                else:
                    await session.rollback()
                    logger.warning(f"Failed to reserve {quantity} units of product {product_id} at location {location_id} - insufficient stock")
                    return False
                    
        except Exception as e:
            logger.error(f"Error reserving stock for product {product_id} at location {location_id}: {e}", exc_info=True)
            return False

    async def release_stock(self, product_id: int, location_id: int, quantity: int) -> bool:
        """
        Releases reserved stock for a product at a specified location.
        
        Increases the available stock by the given quantity, typically used when orders are canceled or rejected.
        
        Args:
            product_id: The ID of the product to update.
            location_id: The ID of the location where stock is released.
            quantity: The number of units to add back to available stock.
        
        Returns:
            True if the stock was successfully released, False otherwise.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                updated_stock = await product_repo.update_stock_quantity(product_id, location_id, quantity)
                if updated_stock:
                    await session.commit()
                    logger.info(f"Released {quantity} units of product {product_id} at location {location_id}")
                    return True
                else:
                    await session.rollback()
                    logger.error(f"Failed to release {quantity} units of product {product_id} at location {location_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error releasing stock for product {product_id} at location {location_id}: {e}", exc_info=True)
            return False

    async def list_all_products_paginated(self, language: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves a paginated list of products with localized names and pricing information.
        
        Each product includes its ID, localized name (with fallback if unavailable), SKU, formatted price for display, and raw price. Returns the list of products and the total count. If an error occurs, returns an empty list and zero.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                products_db, total_count = await product_repo.get_all_products_paginated(offset, limit)
                
                formatted_products = []
                for product in products_db:
                    localized_name = None
                    # Attempt to find localization for the given language
                    for loc in product.localizations:
                        if loc.language_code == language:
                            localized_name = loc.name
                            break
                    # Fallback if no localization found for the current language
                    if not localized_name and product.localizations:
                        localized_name = product.localizations[0].name # Default to first available
                    elif not localized_name:
                         localized_name = f"{get_text('product_fallback_name', language, default='Product')} {product.id}"


                    formatted_products.append({
                        "id": product.id,
                        "name": localized_name, # This is the crucial part for display in lists
                        "sku": product.sku,
                        "price_display": format_price(product.cost, language), # Assuming format_price handles currency
                        "raw_price": product.cost, # Keep raw price for potential calculations
                        # Add other fields if necessary for the list view
                    })
                return formatted_products, total_count
        except Exception as e:
            logger.error(f"Error in list_all_products_paginated: {e}", exc_info=True)
            return [], 0

    async def list_all_categories_paginated(self, language: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves a paginated list of categories with their IDs and names.
        
        Returns:
            A tuple containing a list of category dictionaries and the total count.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                categories_db, total_count = await product_repo.get_all_categories_paginated(offset, limit)
                
                # Categories typically don't have complex localization in this structure, but name is primary.
                # If Category had localizations like Product, similar logic would apply.
                # For now, assume Category.name is sufficient or pre-localized.
                formatted_categories = [{"id": cat.id, "name": cat.name} for cat in categories_db]
                return formatted_categories, total_count
        except Exception as e:
            logger.error(f"Error in list_all_categories_paginated: {e}", exc_info=True)
            return [], 0

    async def list_all_manufacturers_paginated(self, language: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves a paginated list of manufacturers.
        
        Returns:
            A tuple containing a list of manufacturer dictionaries with IDs and names, and the total count of manufacturers. Returns an empty list and zero count if an error occurs.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                manufacturers_db, total_count = await product_repo.get_all_manufacturers_paginated(offset, limit)
                formatted_manufacturers = [{"id": mfg.id, "name": mfg.name} for mfg in manufacturers_db]
                return formatted_manufacturers, total_count
        except Exception as e:
            logger.error(f"Error in list_all_manufacturers_paginated: {e}", exc_info=True)
            return [], 0

    async def list_all_locations_paginated(self, language: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves a paginated list of locations with their IDs, names, and addresses.
        
        Returns:
            A tuple containing a list of location dictionaries and the total count of locations.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                locations_db, total_count = await product_repo.get_all_locations_paginated(offset, limit)
                formatted_locations = [
                    {"id": loc.id, "name": loc.name, "address": loc.address} 
                    for loc in locations_db
                ]
                return formatted_locations, total_count
        except Exception as e:
            logger.error(f"Error in list_all_locations_paginated: {e}", exc_info=True)
            return [], 0

    async def get_locations_for_product_stock_admin(self, product_id: int, language: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
        # For now, this lists all locations. It could be enhanced to show current stock per location for the product.
        """
        Retrieves a paginated list of all locations for product stock administration.
        
        Returns a list of dictionaries containing location IDs, names, and addresses, along with the total count of locations. Currently, the product ID is not used for filtering but is included for future extensibility. Returns an empty list and zero count on error.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                # At this stage, product_id is known but not strictly used by the repo method below.
                # This service method is structured to allow future enhancements.
                locations_db, total_count = await product_repo.get_all_locations_for_product_stock(offset, limit)
                formatted_locations = [
                    {"id": loc.id, "name": loc.name, "address": loc.address} 
                    for loc in locations_db
                ]
                return formatted_locations, total_count
        except Exception as e:
            logger.error(f"Error in get_locations_for_product_stock_admin for product {product_id}: {e}", exc_info=True)
            return [], 0

    async def update_stock_by_admin(self, product_id: int, location_id: int, quantity_change: int, admin_id: int, language: str) -> Tuple[bool, str, Optional[int]]:
        # quantity_change is the amount to add (positive) or subtract (negative)
        """
        Updates the stock quantity for a product at a specific location by an admin, ensuring the resulting stock is not negative.
        
        Args:
            product_id: The ID of the product to update.
            location_id: The ID of the location where the stock is updated.
            quantity_change: The amount to add (positive) or subtract (negative) from the current stock.
            admin_id: The ID of the admin performing the update.
            language: The language code for localization (not used in this method but included for interface consistency).
        
        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message key describing the result.
                - The new stock quantity if successful, the current quantity if the update would result in negative stock, or None if a database error occurred.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                # Get current stock to validate against negative results if needed, though DB constraint should handle it
                current_stock_record = await product_repo.get_stock_record(product_id, location_id)
                current_quantity = current_stock_record.quantity if current_stock_record else 0

                if current_quantity + quantity_change < 0:
                    # This check prevents trying to make stock negative if not allowed by DB or business logic
                    return False, "admin_stock_update_failed_negative_result", current_quantity

                updated_stock = await product_repo.update_stock_quantity(product_id, location_id, quantity_change)
                if updated_stock:
                    await session.commit()
                    logger.info(f"Admin {admin_id} updated stock for product {product_id} at location {location_id} by {quantity_change}. New quantity: {updated_stock.quantity}")
                    return True, "admin_stock_updated_success_with_new_qty", updated_stock.quantity
                else:
                    # This case might be rare if the above negative check is solid and DB constraints are good.
                    # It could mean product_id or location_id is invalid, or another issue.
                    await session.rollback()
                    # The original update_stock_quantity returns None if stock record didn't exist and quantity_change was negative.
                    # This can happen if trying to decrease stock for a product/location pair that has no stock record.
                    return False, "admin_stock_update_failed_general", current_quantity 
                    
        except Exception as e:
            logger.error(f"Error in update_stock_by_admin for product {product_id}, location {location_id}: {e}", exc_info=True)
            return False, "admin_stock_update_failed_db_error", None
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
        Release reserved stock (increase available stock).
        Used when orders are cancelled or rejected.
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


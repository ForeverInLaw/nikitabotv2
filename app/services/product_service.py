"""
Product service for managing product-related business logic.
Handles product CRUD, localization, stock management, and location/manufacturer operations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select # Added import
from sqlalchemy.exc import SQLAlchemyError # Added import

from app.db.database import get_session
from app.db.repositories.product_repo import ProductRepository
from app.db.models import Product, Location, Manufacturer, Category # Ensure Manufacturer and Product are here
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

    async def get_all_entities_paginated(
        self, entity_type: str, page: int, items_per_page: int, language: str = "en"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetches a paginated list of entities (Location or Manufacturer)
        and the total count of such entities.
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                if entity_type == "location":
                    entities, total_count = await product_repo.get_all_locations_paginated(page, items_per_page)
                elif entity_type == "manufacturer":
                    entities, total_count = await product_repo.get_all_manufacturers_paginated(page, items_per_page)
                else:
                    return [], 0
                
                return [{"id": entity.id, "name": entity.name} for entity in entities], total_count
        except Exception as e:
            logger.error(f"Error getting paginated {entity_type}: {e}", exc_info=True)
            return [], 0

    async def get_entity_by_id(
        self, entity_type: str, entity_id: int, language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Fetches a single entity (Location or Manufacturer) by its ID."""
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                entity: Optional[Location | Manufacturer] = None
                if entity_type == "location":
                    entity = await product_repo.get_location_by_id(entity_id)
                elif entity_type == "manufacturer":
                    entity = await product_repo.get_manufacturer_by_id(entity_id)
                
                if entity:
                    return {"id": entity.id, "name": entity.name}
                return None
        except Exception as e:
            logger.error(f"Error getting {entity_type} by ID {entity_id}: {e}", exc_info=True)
            return None

    async def delete_manufacturer_by_id(self, manufacturer_id: int, lang: str) -> Tuple[bool, str, Optional[str]]:
        """
        Deletes a manufacturer by its ID.
        Returns a tuple: (success_status, message_key, optional_manufacturer_name).
        """
        manufacturer_entity = await self.get_entity_by_id("manufacturer", manufacturer_id, lang)
        if not manufacturer_entity:
            return False, "admin_manufacturer_not_found", None
        
        manufacturer_name = manufacturer_entity.get("name")

        try:
            async with get_session() as session: # Use get_session for db interactions
                # Check for linked products
                product_exists_stmt = select(Product).filter_by(manufacturer_id=manufacturer_id).limit(1)
                product_result = await session.execute(product_exists_stmt)
                product = product_result.scalar_one_or_none()

                if product:
                    logger.warning(f"Attempt to delete manufacturer {manufacturer_id} ({manufacturer_name}) failed: linked products exist.")
                    return False, "admin_manufacturer_delete_has_products_error", manufacturer_name

                # Delete manufacturer
                to_delete = await session.get(Manufacturer, manufacturer_id)
                if to_delete:
                    await session.delete(to_delete)
                    await session.commit()
                    logger.info(f"Manufacturer {manufacturer_id} ({manufacturer_name}) deleted successfully.")
                    return True, "admin_manufacturer_deleted_successfully", manufacturer_name
                else:
                    # This case should ideally be caught by get_entity_by_id, but as a fallback:
                    logger.warning(f"Manufacturer {manufacturer_id} ({manufacturer_name}) not found for deletion after initial check.")
                    return False, "admin_manufacturer_not_found", manufacturer_name
        except SQLAlchemyError as e:
            logger.error(f"Database error while deleting manufacturer {manufacturer_id} ({manufacturer_name}): {e}", exc_info=True)
            await session.rollback() # Rollback on error
            return False, "admin_manufacturer_delete_failed", manufacturer_name
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error while deleting manufacturer {manufacturer_id} ({manufacturer_name}): {e}", exc_info=True)
            await session.rollback() # Rollback on error
            return False, "admin_manufacturer_delete_failed", manufacturer_name
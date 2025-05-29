"""
Product service for managing product-related business logic.
Handles product CRUD, localization, stock management, and location/manufacturer operations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, func # Added import
from sqlalchemy.exc import SQLAlchemyError, IntegrityError # Added import
from sqlalchemy.orm import selectinload


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
                        "price": product.price # Changed from product.cost
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
                    "price": product.price, # Changed from product.cost
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
                    return [{"id": entity.id, "name": entity.name} for entity in entities], total_count
                elif entity_type == "manufacturer":
                    entities, total_count = await product_repo.get_all_manufacturers_paginated(page, items_per_page)
                    return [{"id": entity.id, "name": entity.name} for entity in entities], total_count
                elif entity_type == "category":
                    all_categories = await product_repo.list_categories()
                    total_count = len(all_categories)
                    
                    offset = page * items_per_page
                    categories_on_page = all_categories[offset:offset + items_per_page]
                    
                    return [{"id": category.id, "name": category.name} for category in categories_on_page], total_count
                else:
                    return [], 0
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
            # Ensure session is available for rollback; it might not be if get_session() failed.
            if 'session' in locals() and session.is_active:
                 await session.rollback() # Rollback on error
            return False, "admin_manufacturer_delete_failed", manufacturer_name

    async def create_manufacturer(self, name: str, lang: str = "en") -> Tuple[Optional[Dict[str, Any]], str, Optional[int]]:
        """
        Creates a new manufacturer.
        Returns a tuple: (created_manufacturer_dict, message_key, manufacturer_id).
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                created_mfg: Optional[Manufacturer] = await product_repo.create_manufacturer(name=name)
                
                if created_mfg:
                    await session.commit() # Commit only if manufacturer was created by repo and no error
                    logger.info(f"Manufacturer '{created_mfg.name}' (ID: {created_mfg.id}) created successfully.")
                    return (
                        {"id": created_mfg.id, "name": created_mfg.name},
                        "admin_mfg_created_successfully",
                        created_mfg.id
                    )
                else:
                    # This path is taken if repo returns None (duplicate or SQLAlchemyError it handled)
                    # We assume "duplicate" as the primary reason for None if no exception bubbled up.
                    # The repo logs specifics if it was another SQLAlchemyError.
                    await session.rollback() # Ensure rollback if repo returned None for any reason.
                    logger.warning(f"Manufacturer creation failed for name '{name}', likely due to duplicate or DB issue handled by repo.")
                    return None, "admin_mfg_create_failed_duplicate", None
                    
        except SQLAlchemyError as e: # Catch SQLAlchemy errors that might occur if repo re-raises or if session ops fail
            # This block might be redundant if repo catches all SQLAlchemyErrors, but good for safety.
            logger.error(f"Database error during manufacturer creation for name '{name}': {e}", exc_info=True)
            # Attempt to rollback if session is available and active
            if 'session' in locals() and hasattr(session, 'is_active') and session.is_active:
                await session.rollback()
            return None, "admin_mfg_create_failed_db_error", None
        except Exception as e: # Catch any other unexpected errors (e.g., get_session failure)
            logger.error(f"Unexpected error during manufacturer creation for name '{name}': {e}", exc_info=True)
            if 'session' in locals() and hasattr(session, 'is_active') and session.is_active:
                await session.rollback()
            return None, "admin_mfg_create_failed_db_error", None # Generic DB error for unexpected issues

    async def create_category(self, name: str, lang: str = "en") -> Tuple[Optional[Dict[str, Any]], str, Optional[int]]:
        """
        Creates a new category.
        Returns a tuple: (created_category_dict, message_key, category_id).
        """
        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                created_category: Optional[Category] = await product_repo.create_category(name=name)
                
                if created_category:
                    await session.commit()
                    logger.info(f"Category '{created_category.name}' (ID: {created_category.id}) created successfully.")
                    return (
                        {"id": created_category.id, "name": created_category.name},
                        "admin_category_created_successfully",
                        created_category.id
                    )
                else:
                    # This path is taken if repo returns None.
                    # The repo logs IntegrityError vs other SQLAlchemyError.
                    # We need to infer which message to return.
                    # A more robust way would be for the repo to return a specific error type or code.
                    # For now, assume 'duplicate' if no exception bubbled from repo and it returned None.
                    # This relies on the repo's logging to distinguish.
                    await session.rollback() 
                    # Attempt to check if it was a duplicate by trying to fetch it
                    # This is a workaround; ideally, the repo would give a clearer signal.
                    existing_category = await product_repo.get_category_by_name(name)
                    if existing_category:
                        logger.warning(f"Category creation failed for name '{name}', duplicate detected post-attempt.")
                        return None, "admin_category_already_exists_error", None
                    else:
                        logger.warning(f"Category creation failed for name '{name}', repository returned None but not found as duplicate.")
                        return None, "admin_category_create_failed_db_error", None # Generic DB error if not clearly a duplicate
                    
        except SQLAlchemyError as e: # Catch SQLAlchemy errors that might occur if repo re-raises or if session ops fail
            if 'session' in locals() and hasattr(session, 'is_active') and session.is_active:
                await session.rollback()
            logger.error(f"Database error during category creation for name '{name}': {e}", exc_info=True)
            # Check if it's an integrity error (duplicate) specifically, if possible from `e`
            if isinstance(e, IntegrityError): # More specific check
                 return None, "admin_category_already_exists_error", None
            return None, "admin_category_create_failed_db_error", None
        except Exception as e: # Catch any other unexpected errors
            if 'session' in locals() and hasattr(session, 'is_active') and session.is_active:
                await session.rollback()
            logger.error(f"Unexpected error during category creation for name '{name}': {e}", exc_info=True)
            return None, "admin_category_create_failed_unexpected", None

    async def update_manufacturer_details(
        self, manufacturer_id: int, name: str, lang: str = "en"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Updates a manufacturer's details.
        Returns a tuple: (success_status, message_key, optional_updated_manufacturer_details_dict).
        """
        # Get current manufacturer details for logging or pre-check if needed, though not strictly necessary for the update itself
        # current_manufacturer = await self.get_entity_by_id("manufacturer", manufacturer_id, lang)
        # if not current_manufacturer:
        # return False, "admin_manufacturer_not_found", None

        try:
            async with get_session() as session:
                product_repo = ProductRepository(session)
                
                # The repository method should handle the actual update logic
                # It should return the updated manufacturer object or None if not found/not updated
                updated_manufacturer = await product_repo.update_manufacturer(manufacturer_id, name)
                
                if updated_manufacturer:
                    await session.commit()
                    logger.info(f"Manufacturer {manufacturer_id} updated successfully to name '{name}'.")
                    return True, "admin_manufacturer_updated_successfully", {"id": updated_manufacturer.id, "name": updated_manufacturer.name}
                else:
                    # This case might occur if the manufacturer was deleted just before the update.
                    # Or if update_manufacturer returns None for "no change" (though a specific check for that might be better)
                    await session.rollback() # Rollback, as no change was made or target not found by repo method
                    logger.warning(f"Attempted to update manufacturer {manufacturer_id} but it was not found or not updated by repository.")
                    return False, "admin_manufacturer_not_found", None

        except IntegrityError as e:
            # Specific error for duplicate names (assuming name has a unique constraint)
            # The original exception 'e' might contain details about which constraint was violated.
            # logger.error(f"Integrity error while updating manufacturer {manufacturer_id} to name '{name}': {e}", exc_info=True)
            # Check if session is active before rollback
            if 'session' in locals() and session.is_active:
                await session.rollback()
            logger.error(f"Integrity error (likely duplicate name) while updating manufacturer {manufacturer_id} to name '{name}': {e}", exc_info=True)
            return False, "admin_manufacturer_update_failed_duplicate", None
            
        except SQLAlchemyError as e:
            # Generic database error
            if 'session' in locals() and session.is_active:
                await session.rollback()
            logger.error(f"Database error while updating manufacturer {manufacturer_id} to name '{name}': {e}", exc_info=True)
            return False, "admin_manufacturer_update_failed_db_error", None
            
        except Exception as e:
            # Catch any other unexpected errors
            if 'session' in locals() and session.is_active:
                await session.rollback()
            logger.error(f"Unexpected error while updating manufacturer {manufacturer_id} to name '{name}': {e}", exc_info=True)
            return False, "admin_manufacturer_update_failed_unexpected", None

    async def create_product_with_details(
        self,
        admin_id: int, # For logging purposes, not directly used in creation logic here
        product_data: Dict[str, Any],
        localizations_data: List[Dict[str, str]],
        lang: str = "en"  # For error messages, though not heavily used here
    ) -> Tuple[Optional[Product], str, Optional[int]]:
        """
        Creates a new product with its details and localizations.
        Returns a tuple: (created_product_object, message_key, product_id).
        """
        async with get_session() as session:
            try:
                product_repo = ProductRepository(session)

                # Validate Manufacturer ID
                manufacturer_id = product_data.get("manufacturer_id")
                if manufacturer_id:
                    manufacturer = await product_repo.get_manufacturer_by_id(manufacturer_id)
                    if not manufacturer:
                        logger.warning(f"Admin {admin_id} attempting to create product with non-existent manufacturer ID {manufacturer_id}.")
                        return None, "admin_error_manufacturer_not_found", None
                else: # Should be caught by FSM validation, but good to have a safeguard
                    logger.error(f"Admin {admin_id} - product creation attempt without manufacturer_id.")
                    return None, "admin_error_manufacturer_not_found", None


                # Validate Category ID (now mandatory)
                category_id = product_data.get("category_id") # Still use .get() initially to check presence
                if category_id is None: # Explicitly check if it's missing
                    logger.error(f"Admin {admin_id} - product creation attempt without category_id. This should be caught by FSM.")
                    return None, "admin_error_category_not_found", None # Or a more specific error key

                category = await product_repo.get_category_by_id(category_id)
                if not category:
                    logger.warning(f"Admin {admin_id} attempting to create product with non-existent category ID {category_id}.")
                    return None, "admin_error_category_not_found", None
                
                # Convert price back to Decimal before passing to repository
                # Assuming product_data comes in with "price" key from the caller FSM/handler
                product_data["price"] = Decimal(product_data["price"]) # Changed from "cost"

                # Extract product name for the main 'name' field in the Product table
                product_name_for_table = None
                # The existing check for empty localizations_data should prevent issues here,
                # but defensive coding is good.
                if localizations_data: 
                    # Try to find 'en'
                    for loc in localizations_data:
                        if loc.get("language_code") == "en":
                            product_name_for_table = loc.get("name")
                            break
                    # If 'en' not found, use the first available name
                    if not product_name_for_table: # and localizations_data is guaranteed non-empty by prior check
                        product_name_for_table = localizations_data[0].get("name")
                
                # If product_name_for_table is still None here, it implies localizations_data was empty
                # or structured unexpectedly (e.g., missing 'name' key).
                # The existing check `if not localizations_data:` handles the empty case later,
                # but if it *must* be set for create_product, this is the point to ensure it.
                # For now, we rely on the subsequent check to catch empty localizations_data.
                # A more robust solution might involve raising an error or using a default name
                # if product_name_for_table remains None and is strictly required by create_product.

                # Create the product
                # ProductRepository.create_product expects specific args, not a dict
                new_product = await product_repo.create_product(
                    name=product_name_for_table, # Pass the extracted name
                    manufacturer_id=product_data["manufacturer_id"],
                    category_id=product_data["category_id"], # Changed to direct access
                    price=product_data["price"], # Changed from cost=product_data["cost"]
                    variation=product_data.get("variation"), # Optional
                    image_url=product_data.get("image_url") # Optional
                )

                if not new_product or not new_product.id: # Should not happen if create_product is robust
                    await session.rollback()
                    logger.error(f"Admin {admin_id} - product creation failed unexpectedly after repo.create_product call for product with manufacturer ID {product_data.get('manufacturer_id')}.")
                    return None, "admin_product_create_failed_db_error", None
                
                logger.info(f"Admin {admin_id} created product draft ID {new_product.id}.")

                # Add localizations
                if not localizations_data: # Should be caught by FSM, at least one localization needed
                    await session.rollback()
                    logger.warning(f"Admin {admin_id} - product creation attempt for product ID {new_product.id} without localizations.")
                    return None, "admin_product_create_failed_no_localization", new_product.id


                for loc_data in localizations_data:
                    await product_repo.add_or_update_product_localization(
                        product_id=new_product.id,
                        language_code=loc_data["language_code"],
                        name=loc_data["name"],
                        description=loc_data.get("description") # Optional
                    )
                logger.info(f"Admin {admin_id} added {len(localizations_data)} localizations for product ID {new_product.id}.")

                await session.commit()
                logger.info(f"Admin {admin_id} successfully created product ID {new_product.id} with all details.")
                # Fetch the product again to ensure all relationships (like localizations) are loaded for the return object
                # This might be redundant if create_product and add_or_update_product_localization correctly update the new_product object in-session
                # However, to be safe and ensure the returned object is complete:
                created_product_with_rels = await product_repo.get_product_by_id_with_details(new_product.id)

                return created_product_with_rels, "admin_product_created_successfully", new_product.id

            except IntegrityError as e:
                await session.rollback()
                # Basic check for unique constraint violation (could be SKU or other unique fields)
                # More specific parsing of e.orig might be needed if there are multiple unique constraints
                # For example, if e.orig.diag.constraint_name gives the constraint name.
                # Assuming product_sku_key is the unique constraint name for SKU.
                # This is highly database-dependent (PostgreSQL example).
                # if "product_sku_key" in str(e.orig).lower() or "unique constraint" in str(e.orig).lower() and "sku" in str(e.orig).lower():
                # Removed specific SKU check, generic IntegrityError handling below
                
                logger.error(f"Admin {admin_id} - product creation failed due to IntegrityError for product with manufacturer ID {product_data.get('manufacturer_id')}: {e}", exc_info=True)
                return None, "admin_product_create_failed_db_error", None # Generic integrity error

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} - product creation failed due to SQLAlchemyError for product with manufacturer ID {product_data.get('manufacturer_id')}: {e}", exc_info=True)
                return None, "admin_product_create_failed_db_error", None

            except Exception as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} - unexpected error during product creation for product with manufacturer ID {product_data.get('manufacturer_id')}: {e}", exc_info=True)
                return None, "admin_product_create_failed_unexpected", None

    async def get_products_for_admin_list(self, page: int, items_per_page: int, lang: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetches a paginated list of products for the admin panel.
        Formats product names based on the provided language or fallbacks.
        """
        async with get_session() as session:
            product_repo = ProductRepository(session)
            
            # Fetch paginated products with details (localizations, sku, cost)
            # The repository method list_products should ideally allow eager loading of localizations.
            # Assuming list_products is updated or already does this.
            products_on_page = await product_repo.list_products(
                limit=items_per_page, 
                offset=page * items_per_page,
                with_details=True # Ensure this loads localizations
            )
            
            total_count_stmt = select(func.count(Product.id))
            total_count_result = await session.execute(total_count_stmt)
            total_count = total_count_result.scalar_one()

            formatted_products = []
            for product in products_on_page:
                display_name = None
                # Try to get localization for the given lang
                for loc in product.localizations:
                    if loc.language_code == lang:
                        display_name = loc.name
                        break
                # If not found, try for 'en'
                if not display_name:
                    for loc in product.localizations:
                        if loc.language_code == "en":
                            display_name = loc.name
                            break
                # If still not found, use placeholder
                if not display_name:
                    display_name = f"Product ID: {product.id}" # Fallback
                
                formatted_products.append({
                    'id': product.id,
                    'name': display_name, # This name is now ready for display in `create_paginated_keyboard`
                    # 'sku': product.sku if product.sku else get_text("not_set", lang, default="-"), # SKU removed
                    'price': format_price(product.price, lang) # Changed from cost to price
                })
            
            return formatted_products, total_count

    async def get_product_details_for_admin(self, product_id: int, lang: str) -> Optional[Dict[str, Any]]:
        """
        Fetches detailed product information for the admin panel.
        Includes manufacturer, category, all localizations, and stock levels.
        """
        async with get_session() as session:
            product_repo = ProductRepository(session)
            
            # Fetch product with details (manufacturer, category, localizations, stocks with locations)
            # The repository method get_product_by_id should support `with_details=True`
            # to eager load these relationships.
            product = await product_repo.get_product_by_id(product_id, with_details=True)

            if not product:
                return None

            # Basic fields
            details = {
                "id": product.id,
                # "sku": product.sku if product.sku else get_text("not_set", lang, default="-"), # SKU removed
                "variation": product.variation if product.variation else get_text("not_set", lang, default="-"),
                "price": format_price(product.price, lang), # Changed from cost to price
                "image_url": product.image_url, # Will be None if not set, handled by display logic
                "manufacturer_name": product.manufacturer.name if product.manufacturer else get_text("not_assigned", lang, default="N/A"),
                "category_name": product.category.name if product.category else get_text("not_assigned", lang, default="N/A"),
            }

            # Localizations
            localizations_list = []
            for loc in product.localizations:
                localizations_list.append({
                    'lang_code': loc.language_code,
                    'name': loc.name,
                    'description': loc.description if loc.description else get_text("not_set", lang, default="-")
                })
            details["localizations"] = localizations_list

            # Stock Summary
            stock_summary_list = []
            if product.stocks: # product.stocks should be loaded if with_details=True is effective
                for stock_item in product.stocks:
                    # Ensure location is loaded for each stock_item.
                    # If not automatically loaded by with_details=True on product.stocks,
                    # this might require an explicit load option in the repo or a separate query.
                    # For now, assume stock_item.location is available.
                    location_name = stock_item.location.name if stock_item.location else get_text("unknown_location_name", lang)
                    stock_summary_list.append({
                        'location_name': location_name,
                        'quantity': stock_item.quantity
                    })
            details["stock_summary"] = stock_summary_list
            
            return details

    async def update_product_field(
        self, admin_id: int, product_id: int, field_name: str, field_value: Any, lang: str
    ) -> Tuple[bool, str, Optional[Any]]:
        """
        Updates a basic field of a product.
        Returns: (success_status, message_key, new_value_or_None_on_error)
        """
        async with get_session() as session:
            try:
                product_repo = ProductRepository(session)
                
                # Validate product existence
                product = await product_repo.get_product_by_id(product_id)
                if not product:
                    return False, "admin_product_not_found", None

                # Prepare update data
                update_data = {field_name: field_value}

                # Specific validation for certain fields
                if field_name == "price": # Changed from "cost"
                    if not isinstance(field_value, Decimal) or field_value <= 0:
                        return False, "admin_prod_invalid_price_format", None # Changed message key
                elif field_name == "sku":
                    # SKU can be None (optional), but if provided, it's a string.
                    # Unique constraint handled by IntegrityError.
                    # This field is being removed, so this check might become obsolete or be removed.
                    logger.warning(f"Admin {admin_id} attempting to update SKU, which is being deprecated.")
                    # Depending on strictness, could return an error here, or allow if DB still has column
                    pass 
                
                updated_product = await product_repo.update_product(product_id, **update_data)
                if not updated_product: # Should not happen if product was found and update is simple
                    await session.rollback()
                    return False, "admin_prod_update_failed_generic", None

                await session.commit()
                logger.info(f"Admin {admin_id} updated product {product_id} field '{field_name}' to '{field_value}'.")
                
                # Return the actual value set on the model, if different (e.g. Decimal precision)
                # For simplicity, returning the input field_value if successful.
                return True, "admin_prod_updated_field_successfully", field_value

            except IntegrityError as e:
                await session.rollback()
                # Specific SKU duplicate check removed as SKU field is being removed.
                # if "product_sku_key" in str(e.orig).lower() or \
                #    (hasattr(e.orig, 'diag') and hasattr(e.orig.diag, 'constraint_name') and e.orig.diag.constraint_name == 'product_sku_key'):
                #     logger.warning(f"Admin {admin_id} failed to update SKU for product {product_id} due to duplicate: {e}")
                #     return False, "admin_product_update_failed_sku_duplicate", field_value # Return attempted value
                logger.error(f"Admin {admin_id} failed to update product {product_id} field '{field_name}' due to IntegrityError: {e}", exc_info=True)
                return False, "admin_prod_update_failed_db_error", None
            
            except ValueError as e: # Catch specific ValueErrors like for cost
                await session.rollback()
                logger.warning(f"Admin {admin_id} failed to update product {product_id} field '{field_name}' due to ValueError: {e}")
                return False, "admin_prod_invalid_input_for_field", None

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} failed to update product {product_id} field '{field_name}' due to SQLAlchemyError: {e}", exc_info=True)
                return False, "admin_prod_update_failed_db_error", None
            
            except Exception as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} - unexpected error updating product {product_id} field '{field_name}': {e}", exc_info=True)
                return False, "admin_prod_update_failed_unexpected", None

    async def update_product_association(
        self, admin_id: int, product_id: int, association_type: str, associated_id: Optional[int], lang: str
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Updates a product's association (manufacturer or category).
        `association_type` should be 'manufacturer' or 'category'.
        `associated_id` can be None if setting category to None.
        Returns: (success_status, message_key, new_associated_id_or_None_on_error)
        """
        async with get_session() as session:
            try:
                product_repo = ProductRepository(session)

                # Validate product existence
                product = await product_repo.get_product_by_id(product_id)
                if not product:
                    return False, "admin_product_not_found", None

                field_name_to_update = f"{association_type}_id" # e.g., manufacturer_id or category_id

                # Validate associated entity if ID is provided
                if associated_id is not None:
                    if association_type == "manufacturer":
                        entity = await product_repo.get_manufacturer_by_id(associated_id)
                        if not entity:
                            return False, "admin_error_manufacturer_not_found", None
                    elif association_type == "category":
                        entity = await product_repo.get_category_by_id(associated_id)
                        if not entity:
                            return False, "admin_error_category_not_found", None
                    else: # Should not happen
                        return False, "admin_prod_update_failed_invalid_association", None
                elif association_type == "manufacturer" and associated_id is None:
                    # Manufacturer cannot be None for a product
                    return False, "admin_prod_error_manufacturer_cannot_be_none", None
                
                # Category can be None, so associated_id=None is valid for category_id

                updated_product = await product_repo.update_product(product_id, **{field_name_to_update: associated_id})
                if not updated_product: # Should not happen if product and associated entity exist
                    await session.rollback()
                    return False, "admin_prod_update_failed_generic", None
                
                await session.commit()
                logger.info(f"Admin {admin_id} updated product {product_id} association '{association_type}' to ID '{associated_id}'.")
                return True, "admin_prod_updated_association_successfully", associated_id

            except SQLAlchemyError as e: # Covers IntegrityError for foreign key violations if associated_id is invalid
                await session.rollback()
                logger.error(f"Admin {admin_id} failed to update product {product_id} association '{association_type}' to ID '{associated_id}' due to SQLAlchemyError: {e}", exc_info=True)
                return False, "admin_prod_update_failed_db_error_association", None
            
            except Exception as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} - unexpected error updating product {product_id} association '{association_type}': {e}", exc_info=True)
                return False, "admin_prod_update_failed_unexpected", None

    async def add_or_update_product_localization_service(
        self, admin_id: int, product_id: int, loc_lang_code: str, name: str, description: Optional[str], lang: str
    ) -> Tuple[bool, str]:
        """
        Adds or updates a product localization.
        Returns: (success_status, message_key)
        """
        async with get_session() as session:
            try:
                product_repo = ProductRepository(session)
                
                # Validate product existence
                product = await product_repo.get_product_by_id(product_id)
                if not product:
                    return False, "admin_product_not_found" # No product_name for this key

                await product_repo.add_or_update_product_localization(
                    product_id=product_id,
                    language_code=loc_lang_code,
                    name=name,
                    description=description
                )
                await session.commit()
                logger.info(f"Admin {admin_id} added/updated localization for product {product_id} (Lang: {loc_lang_code}, Name: {name}).")
                # Determine if it was an add or update for message key (optional, repo method doesn't directly tell us)
                # For simplicity, using a generic success message for now.
                return True, "admin_prod_localization_saved_successfully"

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} failed to save localization for product {product_id} (Lang: {loc_lang_code}) due to SQLAlchemyError: {e}", exc_info=True)
                return False, "admin_prod_localization_save_failed_db"
            
            except Exception as e:
                await session.rollback()
                logger.error(f"Admin {admin_id} - unexpected error saving localization for product {product_id} (Lang: {loc_lang_code}): {e}", exc_info=True)
                return False, "admin_prod_localization_save_failed_unexpected"

    async def delete_product_by_admin(self, admin_id: int, product_id: int, lang: str) -> Tuple[bool, str, Optional[str]]:
        """
        Deletes a product by its ID.
        Returns a tuple: (success_status, message_key, optional_product_name).
        product_name is returned for use in messages.
        """
        product_display_name = f"ID {product_id}" # Default display name

        # Attempt to get product details for a more user-friendly name in messages
        try:
            product_details = await self.get_product_details_for_admin(product_id, lang)
            if not product_details:
                logger.warning(f"Admin {admin_id} attempting to delete non-existent product ID {product_id}.")
                return False, "admin_product_not_found", None
            
            # Try to get a good display name
            if product_details.get("localizations"):
                name_found = False
                for loc in product_details["localizations"]:
                    if loc['lang_code'] == lang:
                        product_display_name = loc['name']
                        name_found = True
                        break
                if not name_found: # Fallback to English or first localization
                    for loc in product_details["localizations"]:
                        if loc['lang_code'] == "en":
                            product_display_name = loc['name']
                            name_found = True
                            break
                    if not name_found and product_details["localizations"]:
                            product_display_name = product_details["localizations"][0]['name'] # First available
            # Fallback to variation or ID if SKU is removed and no localizations
            elif product_details.get("variation"):
                product_display_name = product_details.get("variation")
            # else: product_display_name remains "ID {product_id}"
            
        except Exception as e_fetch: # Catch errors during detail fetching but still allow delete attempt
            logger.error(f"Error fetching product details for product {product_id} before deletion by admin {admin_id}: {e_fetch}", exc_info=True)
            # product_display_name remains "ID {product_id}"

        async with get_session() as session:
            try:
                product_repo = ProductRepository(session)
                
                # The repository's delete_product method is expected to return False
                # if an IntegrityError (due to RESTRICT constraint) occurs.
                success = await product_repo.delete_product(product_id)
                
                if success:
                    await session.commit()
                    logger.info(f"Admin {admin_id} successfully deleted product ID {product_id} (Display Name: '{product_display_name}').")
                    return True, "admin_product_deleted_successfully", product_display_name
                else:
                    # This implies an IntegrityError was caught in the repository,
                    # likely because the product is referenced by an OrderItem.
                    await session.rollback() # Should be handled in repo, but ensure here.
                    logger.warning(f"Admin {admin_id} failed to delete product ID {product_id} (Display Name: '{product_display_name}') due to it being in use (e.g., in an order).")
                    return False, "admin_product_delete_failed_in_use", product_display_name

            except SQLAlchemyError as e: # Catch other DB errors not handled as False by repo
                await session.rollback()
                logger.error(f"Admin {admin_id} failed to delete product ID {product_id} (Display Name: '{product_display_name}') due to SQLAlchemyError: {e}", exc_info=True)
                return False, "admin_product_delete_failed_generic", product_display_name
            
            except Exception as e: # Catch any other unexpected errors
                await session.rollback()
                logger.error(f"Admin {admin_id} - unexpected error deleting product ID {product_id} (Display Name: '{product_display_name}'): {e}", exc_info=True)
                return False, "admin_product_delete_failed_unexpected", product_display_name
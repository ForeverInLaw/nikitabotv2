from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
import logging # Added for logging

from app.db.repositories.location_repo import LocationRepository
from app.db.models import Location
from app.localization.locales import get_text # For messages

logger = logging.getLogger(__name__) # Added logger

class LocationService:
    def __init__(self):
        self.repo = LocationRepository() # In a larger app, use dependency injection

    def _format_location_for_admin(self, location: Location, lang: str) -> Dict[str, Any]:
        """Formats a Location object into a dictionary for admin display."""
        if not location:
            return {}
        return {
            "id": location.id,
            "name": location.name,
            "address": location.address if location.address else get_text("not_specified_placeholder", lang, default="Not specified"),
            "created_at": location.created_at.strftime("%Y-%m-%d %H:%M:%S") if location.created_at else "N/A",
            "updated_at": location.updated_at.strftime("%Y-%m-%d %H:%M:%S") if location.updated_at else "N/A",
            # For use in paginated keyboards
            "display_name": f"{location.name} ({location.address or get_text('no_address_placeholder', lang, default='No address')})"
        }

    async def create_location(self, name: str, address: Optional[str], lang: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Creates a new location. Returns (location_dict, error_message_key)."""
        try:
            existing_location = await self.repo.get_location_by_name(name)
            if existing_location:
                return None, "admin_location_already_exists_error"
            
            new_location = await self.repo.add_location(name=name, address=address)
            if new_location:
                return self._format_location_for_admin(new_location, lang), None
            else:
                return None, "admin_location_create_failed_error"
        except SQLAlchemyError as e:
            logger.error(f"Error creating location {name}: {e}")
            return None, "admin_db_error_generic"
        except Exception as e:
            logger.error(f"Unexpected error creating location {name}: {e}")
            return None, "admin_unexpected_error_generic"

    async def get_location_details(self, location_id: int, lang: str) -> Optional[Dict[str, Any]]:
        """Gets details for a single location, formatted for admin."""
        try:
            location = await self.repo.get_location_by_id(location_id)
            if location:
                return self._format_location_for_admin(location, lang)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching location {location_id}: {e}")
            return None # Or raise a service layer exception
        except Exception as e:
            logger.error(f"Unexpected error fetching location {location_id}: {e}")
            return None

    async def get_all_locations_paginated(self, page: int, limit: int, lang: str) -> Tuple[List[Dict[str, Any]], int]:
        """Gets a paginated list of locations, formatted for admin display."""
        try:
            skip = page * limit
            locations_list, total_count = await self.repo.list_locations(skip=skip, limit=limit)
            formatted_locations = [self._format_location_for_admin(loc, lang) for loc in locations_list]
            return formatted_locations, total_count
        except SQLAlchemyError as e:
            logger.error(f"Error listing locations: {e}")
            return [], 0
        except Exception as e:
            logger.error(f"Unexpected error listing locations: {e}")
            return [], 0

    async def update_location_details(self, location_id: int, name: Optional[str], address: Optional[str], lang: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Updates a location. Returns (updated_location_dict, error_message_key)."""
        try:
            # Check if new name conflicts with an existing location (if name is being changed)
            if name:
                existing_location_with_name = await self.repo.get_location_by_name(name)
                if existing_location_with_name and existing_location_with_name.id != location_id:
                    return None, "admin_location_name_exists_error"

            updated_location = await self.repo.update_location(location_id, name, address)
            if updated_location:
                return self._format_location_for_admin(updated_location, lang), None
            else:
                # Could be not found or DB error during update in repo
                # Check if it exists to give a more specific error
                if not await self.repo.get_location_by_id(location_id):
                    return None, "admin_location_not_found_error"
                return None, "admin_location_update_failed_error"
        except SQLAlchemyError as e:
            logger.error(f"Error updating location {location_id}: {e}")
            return None, "admin_db_error_generic"
        except Exception as e:
            logger.error(f"Unexpected error updating location {location_id}: {e}")
            return None, "admin_unexpected_error_generic"

    async def delete_location_by_id(self, location_id: int, lang: str) -> Tuple[bool, str, Optional[str]]:
        """Deletes a location. Returns (success_bool, message_key, location_name_optional)."""
        location_name = None
        try:
            location_to_delete = await self.repo.get_location_by_id(location_id)
            if not location_to_delete:
                return False, "admin_location_not_found_error", None
            location_name = location_to_delete.name

            # The repository's delete_location method already checks for dependencies.
            deleted = await self.repo.delete_location(location_id)
            if deleted:
                return True, "admin_location_deleted_successfully", location_name
            else:
                # Deletion could fail due to dependencies or other DB issues not caught as SQLAlchemyError by repo
                # Or if the repo's dependency check returned False.
                # Check again if it's due to dependencies by trying to fetch it (it should exist)
                current_location_state = await self.repo.get_location_by_id(location_id)
                if current_location_state and (current_location_state.product_stocks or current_location_state.order_items or current_location_state.cart_items):
                    return False, "admin_location_delete_has_dependencies_error", location_name
                return False, "admin_location_delete_failed_error", location_name
        except SQLAlchemyError as e:
            logger.error(f"Error deleting location {location_id}: {e}")
            return False, "admin_db_error_generic", location_name
        except Exception as e:
            logger.error(f"Unexpected error deleting location {location_id}: {e}")
            return False, "admin_unexpected_error_generic", location_name

from typing import Optional, List, Tuple

from sqlalchemy import select, func, update # Removed 'delete' as it's not used with session.delete()
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location
# Assuming async_session_maker is correctly defined in app.db.database
from app.db.database import async_session_maker 

class LocationRepository:
    def __init__(self, session_factory=async_session_maker):
        self.session_factory = session_factory

    async def add_location(self, name: str, address: Optional[str] = None) -> Optional[Location]:
        async with self.session_factory() as session:
            try:
                new_location = Location(name=name, address=address)
                session.add(new_location)
                await session.commit()
                await session.refresh(new_location)
                return new_location
            except SQLAlchemyError as e:
                # In a real app, log error e
                await session.rollback()
                return None

    async def get_location_by_id(self, location_id: int) -> Optional[Location]:
        async with self.session_factory() as session:
            try:
                result = await session.execute(select(Location).filter_by(id=location_id))
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                # In a real app, log error e
                return None

    async def get_location_by_name(self, name: str) -> Optional[Location]:
        async with self.session_factory() as session:
            try:
                result = await session.execute(select(Location).filter_by(name=name))
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                # In a real app, log error e
                return None

    async def list_locations(self, skip: int = 0, limit: int = 100) -> Tuple[List[Location], int]:
        async with self.session_factory() as session:
            try:
                count_query = select(func.count()).select_from(Location)
                total_count_result = await session.execute(count_query)
                total_count = total_count_result.scalar_one()

                query = select(Location).offset(skip).limit(limit).order_by(Location.name)
                result = await session.execute(query)
                locations = result.scalars().all()
                return list(locations), total_count
            except SQLAlchemyError as e:
                # In a real app, log error e
                return [], 0

    async def update_location(self, location_id: int, name: Optional[str] = None, address: Optional[str] = None) -> Optional[Location]:
        if name is None and address is None:
            async with self.session_factory() as session:
                 return await session.get(Location, location_id) # Return current if no changes

        async with self.session_factory() as session:
            try:
                location = await session.get(Location, location_id)
                if not location:
                    return None

                values_to_update = {}
                if name is not None:
                    location.name = name # Update attribute directly
                if address is not None:
                    location.address = address # Update attribute directly
                
                await session.commit()
                await session.refresh(location)
                return location
            except SQLAlchemyError as e:
                # In a real app, log error e
                await session.rollback()
                return None

    async def delete_location(self, location_id: int) -> bool:
        async with self.session_factory() as session:
            try:
                location = await session.get(Location, location_id)
                if not location:
                    return False # Not found

                # Basic check for dependencies (can be enhanced or rely on DB constraints)
                # These relationship names must match your Location model definition
                if location.product_stocks or location.order_items or location.cart_items:
                    # Log attempt to delete location with dependencies
                    return False # Deletion failed due to dependencies

                await session.delete(location)
                await session.commit()
                return True
            except SQLAlchemyError as e:
                # In a real app, log error e
                await session.rollback()
                return False

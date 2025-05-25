"""
User repository for database operations.
Data access layer for user-related database queries.
"""

import logging
from typing import Optional, List
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Admin

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user data access operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, telegram_id: int, language_code: str = "en") -> User:
        """Create new user."""
        user = User(telegram_id=telegram_id, language_code=language_code)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user) # Ensure all attributes are loaded, including defaults
        return user
    
    async def update_language(self, user: User, language_code: str) -> User:
        """Update user language."""
        user.language_code = language_code
        # The commit will be handled by the service layer
        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def is_admin(self, telegram_id: int) -> bool:
        """Check if user is admin."""
        result = await self.session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None
    
    # The methods below were for direct instance modification without explicit flush/commit here.
    # Admin actions will use update_user_block_status for clarity and directness.
    # async def block_user(self, user: User) -> User:
    #     """Block user."""
    #     user.is_blocked = True
    #     return user
    
    # async def unblock_user(self, user: User) -> User:
    #     """Unblock user."""
    #     user.is_blocked = False
    #     return user

    async def list_users(self, limit: int = 20, offset: int = 0, is_blocked: Optional[bool] = None) -> List[User]:
        """List all users with optional filtering by block status."""
        stmt = select(User).order_by(User.created_at.desc())
        if is_blocked is not None:
            stmt = stmt.where(User.is_blocked == is_blocked)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_users(self, is_blocked: Optional[bool] = None) -> int:
        """Count total users with optional filtering by block status."""
        stmt = select(func.count(User.telegram_id))
        if is_blocked is not None:
            stmt = stmt.where(User.is_blocked == is_blocked)
        result = await self.session.execute(stmt)
        return result.scalar_one()
        
    async def update_user_block_status(self, telegram_id: int, is_blocked: bool) -> Optional[User]:
        """Update user's block status. Returns the updated user or None if not found."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            if user.is_blocked == is_blocked: # No change needed
                return user 
            user.is_blocked = is_blocked
            await self.session.flush()
            await self.session.refresh(user)
            return user
        return None

    async def add_admin(self, telegram_id: int, role: str = "admin") -> Optional[Admin]:
        """Make a user an admin. Ensures user exists first."""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            logger.warning(f"Attempted to make non-existent user {telegram_id} an admin.")
            return None
        
        existing_admin = await self.session.get(Admin, telegram_id)
        if existing_admin:
            existing_admin.role = role # Update role if already admin
            admin_record = existing_admin
        else:
            admin_record = Admin(telegram_id=telegram_id, role=role)
            self.session.add(admin_record)
        
        await self.session.flush()
        await self.session.refresh(admin_record)
        return admin_record

    async def remove_admin(self, telegram_id: int) -> bool:
        """Remove admin privileges from a user."""
        admin_record = await self.session.get(Admin, telegram_id)
        if admin_record:
            await self.session.delete(admin_record)
            await self.session.flush()
            return True
        return False




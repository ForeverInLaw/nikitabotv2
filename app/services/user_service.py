"""
User service for managing user-related business logic.
Handles user creation, language settings, admin operations, and statistics.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from app.db.database import get_session
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.order_repo import OrderRepository
from app.db.models import User
from app.localization.locales import get_text
from app.utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""

    async def get_or_create_user(self, telegram_id: int, language_code: str = "en") -> Tuple[Optional[User], bool]:
        """
        Get existing user or create new one.
        Returns (User, is_new) where is_new indicates if user was just created.
        """
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user:
                    return user, False
                    
                # Create new user
                user = await user_repo.create(telegram_id, language_code)
                await session.commit()
                logger.info(f"Created new user: {telegram_id}")
                return user, True
                
        except Exception as e:
            logger.error(f"Error in get_or_create_user for {telegram_id}: {e}", exc_info=True)
            return None, False

    async def get_user_by_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                return await user_repo.get_by_telegram_id(telegram_id)
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}", exc_info=True)
            return None

    async def set_user_language(self, telegram_id: int, language_code: str) -> bool:
        """Set user language preference."""
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                
                user = await user_repo.get_by_telegram_id(telegram_id)
                if not user:
                    logger.warning(f"Attempted to set language for non-existent user: {telegram_id}")
                    return False
                    
                await user_repo.update_language(user, language_code)
                await session.commit()
                logger.info(f"Updated language for user {telegram_id} to {language_code}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting language for user {telegram_id}: {e}", exc_info=True)
            return False

    async def is_admin(self, telegram_id: int) -> bool:
        """Check if user has admin privileges."""
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                return await user_repo.is_admin(telegram_id)
        except Exception as e:
            logger.error(f"Error checking admin status for user {telegram_id}: {e}", exc_info=True)
            return False

    async def list_users_for_admin(
        self, 
        language: str = "en",
        limit: int = 20, 
        offset: int = 0,
        is_blocked_filter: Optional[bool] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List users for admin with formatting.
        Returns (formatted_users, total_count).
        """
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                
                users = await user_repo.list_users(limit, offset, is_blocked_filter)
                total_count = await user_repo.count_users(is_blocked_filter)
                
                formatted_users = []
                for user in users:
                    status_emoji = "🔒" if user.is_blocked else "🔓"
                    lang_display = user.language_code.upper()
                    
                    formatted_users.append({
                        "telegram_id": user.telegram_id,
                        "name": f"User ID: {user.telegram_id} ({lang_display}) {status_emoji}",
                        "language_code": user.language_code,
                        "is_blocked": user.is_blocked,
                        "created_at_display": format_datetime(user.created_at, language)
                    })
                
                return formatted_users, total_count
                
        except Exception as e:
            logger.error(f"Error listing users for admin: {e}", exc_info=True)
            return [], 0

    async def get_user_details_for_admin(self, telegram_id: int, language: str = "en") -> Optional[Dict[str, Any]]:
        """Get detailed user information for admin view."""
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                order_repo = OrderRepository(session)
                
                user = await user_repo.get_by_telegram_id(telegram_id)
                if not user:
                    return None
                
                # Get order count
                order_count = await order_repo.count_user_orders(telegram_id)
                
                # Check admin status
                is_admin_status = await user_repo.is_admin(telegram_id)
                
                return {
                    "telegram_id": user.telegram_id,
                    "language_code": user.language_code,
                    "is_blocked": user.is_blocked,
                    "is_admin_status": is_admin_status,
                    "order_count": order_count,
                    "created_at_display": format_datetime(user.created_at, language),
                    "updated_at_display": format_datetime(user.updated_at, language)
                }
                
        except Exception as e:
            logger.error(f"Error getting user details for admin {telegram_id}: {e}", exc_info=True)
            return None

    async def block_user_by_admin(self, telegram_id: int, admin_id: int) -> Tuple[bool, str]:
        """
        Block a user by admin action.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                
                result_user = await user_repo.update_user_block_status(telegram_id, True)
                if result_user:
                    await session.commit()
                    logger.warning(f"Admin {admin_id} blocked user {telegram_id}")
                    return True, "admin_user_blocked_success"
                else:
                    return False, "admin_user_block_failed"
                    
        except Exception as e:
            logger.error(f"Error blocking user {telegram_id} by admin {admin_id}: {e}", exc_info=True)
            return False, "admin_user_block_failed_db"

    async def unblock_user_by_admin(self, telegram_id: int, admin_id: int) -> Tuple[bool, str]:
        """
        Unblock a user by admin action.
        Returns (success, message_key).
        """
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                
                result_user = await user_repo.update_user_block_status(telegram_id, False)
                if result_user:
                    await session.commit()
                    logger.info(f"Admin {admin_id} unblocked user {telegram_id}")
                    return True, "admin_user_unblocked_success"
                else:
                    return False, "admin_user_unblock_failed"
                    
        except Exception as e:
            logger.error(f"Error unblocking user {telegram_id} by admin {admin_id}: {e}", exc_info=True)
            return False, "admin_user_unblock_failed_db"

    async def get_basic_statistics(self, language: str = "en") -> Dict[str, Any]:
        """Get basic bot statistics for admin view."""
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                order_repo = OrderRepository(session)
                
                # User statistics
                total_users = await user_repo.count_users()
                active_users = await user_repo.count_users(is_blocked=False)
                blocked_users = await user_repo.count_users(is_blocked=True)
                
                # Order statistics
                total_orders = await order_repo.count_orders()
                pending_orders = await order_repo.count_orders(status="pending_admin_approval")
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "blocked_users": blocked_users,
                    "total_orders": total_orders,
                    "pending_orders": pending_orders
                }
                
        except Exception as e:
            logger.error(f"Error getting basic statistics: {e}", exc_info=True)
            return {
                "total_users": 0,
                "active_users": 0,
                "blocked_users": 0,
                "total_orders": 0,
                "pending_orders": 0
            }


"""
Helper functions and utilities used throughout the application.
Includes enums, formatters, validators, and utility functions.
"""

import logging
import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Union

logger = logging.getLogger(__name__)


class OrderStatusEnum(Enum):
    """Order status enumeration."""
    PENDING_ADMIN_APPROVAL = "pending_admin_approval"
    APPROVED = "approved" 
    PROCESSING = "processing"
    READY_FOR_PICKUP = "ready_for_pickup"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    
    @classmethod
    def values(cls):
        """Get list of all status values."""
        return [status.value for status in cls]


def format_price(amount: Union[Decimal, float, int], currency: str = "$") -> str:
    """Format price for display."""
    try:
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        
        # Format to 2 decimal places
        formatted = f"{amount:.2f}"
        
        # Remove unnecessary trailing zeros
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        
        return f"{currency}{formatted}"
        
    except Exception as e:
        logger.error(f"Error formatting price {amount}: {e}")
        return f"{currency}0.00"


def format_datetime(dt: datetime, language: str = "en") -> str:
    """Format datetime for display based on language."""
    try:
        if language == "ru":
            return dt.strftime("%d.%m.%Y %H:%M")
        elif language == "pl":
            return dt.strftime("%d.%m.%Y %H:%M")
        else:  # Default to English
            return dt.strftime("%m/%d/%Y %H:%M")
            
    except Exception as e:
        logger.error(f"Error formatting datetime {dt}: {e}")
        return str(dt)


def get_order_status_emoji(status: str) -> str:
    """Get emoji for order status."""
    emoji_map = {
        OrderStatusEnum.PENDING_ADMIN_APPROVAL.value: "⏳",
        OrderStatusEnum.APPROVED.value: "✅", 
        OrderStatusEnum.PROCESSING.value: "⚙️",
        OrderStatusEnum.READY_FOR_PICKUP.value: "📦",
        OrderStatusEnum.SHIPPED.value: "🚚",
        OrderStatusEnum.COMPLETED.value: "🎉",
        OrderStatusEnum.CANCELLED.value: "❌",
        OrderStatusEnum.REJECTED.value: "🚫"
    }
    return emoji_map.get(status, "❓")


def get_payment_method_emoji(payment_method: str) -> str:
    """Get emoji for payment method."""
    emoji_map = {
        "cash": "💵",
        "card": "💳",
        "online": "🌐"
    }
    return emoji_map.get(payment_method.lower(), "💰")


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user text input."""
    if not text or not isinstance(text, str):
        return ""
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove potentially harmful characters but keep basic punctuation
    # Allow letters, numbers, spaces, and common punctuation
    sanitized = re.sub(r'[^\w\s\-.,!?():]', '', text)
    
    return sanitized


def validate_quantity(quantity_text: str) -> Optional[int]:
    """
    Validate and parse quantity input.
    Returns None if invalid, positive integer if valid.
    """
    try:
        if not quantity_text or not isinstance(quantity_text, str):
            return None
            
        # Remove whitespace
        quantity_text = quantity_text.strip()
        
        # Try to parse as integer
        quantity = int(quantity_text)
        
        # Must be positive
        if quantity <= 0:
            return None
            
        # Reasonable upper limit
        if quantity > 10000:
            return None
            
        return quantity
        
    except (ValueError, TypeError):
        return None


def validate_stock_change_quantity(quantity_text: str) -> Optional[int]:
    """
    Validate stock change quantity (can be negative for decreases).
    Returns None if invalid, integer if valid.
    """
    try:
        if not quantity_text or not isinstance(quantity_text, str):
            return None
            
        # Remove whitespace
        quantity_text = quantity_text.strip()
        
        # Handle + or - prefix
        if quantity_text.startswith(('+', '-')):
            quantity_text = quantity_text[1:]
        
        # Try to parse as integer
        quantity = int(quantity_text)
        
        # Reasonable limits
        if abs(quantity) > 10000:
            return None
            
        return quantity
        
    except (ValueError, TypeError):
        return None


def validate_decimal(value_text: str, min_value: float = 0.01, max_value: float = 999999.99) -> Optional[Decimal]:
    """
    Validate and parse decimal value (e.g., for prices).
    Returns None if invalid, Decimal if valid.
    """
    try:
        if not value_text or not isinstance(value_text, str):
            return None
            
        # Remove whitespace and currency symbols
        value_text = value_text.strip().replace('$', '').replace('€', '').replace('₽', '')
        
        # Try to parse as Decimal
        value = Decimal(value_text)
        
        # Check bounds
        if value < Decimal(str(min_value)) or value > Decimal(str(max_value)):
            return None
            
        return value
        
    except (ValueError, TypeError, ArithmeticError):
        return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with optional suffix."""
    if not text or len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """Escape special markdown characters in text."""
    if not text:
        return ""
        
    # Characters that need escaping in Telegram markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
        
    return text


def validate_telegram_id(telegram_id_text: str) -> Optional[int]:
    """
    Validate Telegram user ID.
    Returns None if invalid, integer if valid.
    """
    try:
        if not telegram_id_text or not isinstance(telegram_id_text, str):
            return None
            
        telegram_id = int(telegram_id_text.strip())
        
        # Telegram user IDs are positive integers
        # Typical range is from 1 to around 10^10
        if telegram_id <= 0 or telegram_id > 10**10:
            return None
            
        return telegram_id
        
    except (ValueError, TypeError):
        return None


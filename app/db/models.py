"""
SQLAlchemy models for the Telegram bot database schema.
Defines all database tables and relationships.
Includes models for users, orders, products, inventory, etc.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint, CheckConstraint, Enum as DBEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.utils.helpers import OrderStatusEnum # Import the enum

Base = declarative_base()

class User(Base):
    """Telegram users table."""
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    language_code: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    cart_items: Mapped[List["UserCart"]] = relationship("UserCart", back_populates="user", cascade="all, delete-orphan")
    admin_info: Mapped[Optional["Admin"]] = relationship("Admin", back_populates="user", uselist=False)

class Location(Base):
    """Warehouses/store locations table."""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    product_stocks: Mapped[List["ProductStock"]] = relationship("ProductStock", back_populates="location", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="location")
    cart_items: Mapped[List["UserCart"]] = relationship("UserCart", back_populates="location")

class Manufacturer(Base):
    """Product manufacturers table."""
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    products: Mapped[List["Product"]] = relationship("Product", back_populates="manufacturer", cascade="all, delete-orphan")


class Category(Base):
    """Product categories table."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    """Products table."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(Integer, ForeignKey("manufacturers.id"), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variation: Mapped[Optional[str]] = mapped_column(String(255))
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False) # Price
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    manufacturer: Mapped["Manufacturer"] = relationship("Manufacturer", back_populates="products")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    localizations: Mapped[List["ProductLocalization"]] = relationship("ProductLocalization", back_populates="product", cascade="all, delete-orphan")
    stocks: Mapped[List["ProductStock"]] = relationship("ProductStock", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product") 
    cart_items: Mapped[List["UserCart"]] = relationship("UserCart", back_populates="product", cascade="all, delete-orphan")


class ProductLocalization(Base):
    """Product name and description translations."""
    __tablename__ = "product_localization"

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    language_code: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="localizations")


class ProductStock(Base):
    """Product inventory by location."""
    __tablename__ = "product_stock"

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('product_id', 'location_id', name='_product_location_uc'),
        CheckConstraint("quantity >= 0", name="positive_quantity"),
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stocks")
    location: Mapped["Location"] = relationship("Location", back_populates="product_stocks")

class Order(Base):
    """Customer orders."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    # Using SQLAlchemy's Enum type for status if DB supports it, otherwise String.
    # For broader compatibility, String is often used, with validation at app level.
    # The provided OrderStatusEnum.values() can be used for CheckConstraint if Enum type is not desired.
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=OrderStatusEnum.PENDING_ADMIN_APPROVAL.value)
    # status: Mapped[OrderStatusEnum] = mapped_column(DBEnum(OrderStatusEnum, name="order_status_enum", create_type=False), 
    #                                              nullable=False, default=OrderStatusEnum.PENDING_ADMIN_APPROVAL)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., "cash", "card", "online"
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    admin_notes: Mapped[Optional[str]] = mapped_column(Text) # Notes by admin, e.g., rejection reason

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(status.in_(OrderStatusEnum.values()), name='ck_order_status'),
    )


class OrderItem(Base):
    """Individual items within orders."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Quantity deducted from stock
    price_at_order: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False) # Price of product at the time of order

    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_order_quantity"),
        CheckConstraint("reserved_quantity >= 0", name="non_negative_reserved"),
        CheckConstraint("reserved_quantity <= quantity", name="reserved_not_exceeds_ordered"),
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
    location: Mapped["Location"] = relationship("Location", back_populates="order_items")


class UserCart(Base):
    """User shopping cart items."""
    __tablename__ = "user_cart"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', 'location_id', name='_user_product_location_uc_cart'),
        CheckConstraint("quantity > 0", name="positive_cart_quantity"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cart_items")
    product: Mapped["Product"] = relationship("Product", back_populates="cart_items")
    location: Mapped["Location"] = relationship("Location", back_populates="cart_items")


class InterfaceText(Base):
    """Localized interface texts."""
    __tablename__ = "interface_texts"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    text_ru: Mapped[Optional[str]] = mapped_column(Text)
    text_en: Mapped[Optional[str]] = mapped_column(Text)
    text_pl: Mapped[Optional[str]] = mapped_column(Text)


class Admin(Base):
    """Admin users."""
    __tablename__ = "admins"

    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False) # e.g., "admin", "super_admin"

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="admin_info")






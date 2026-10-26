from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Date, DateTime, CheckConstraint, ForeignKey, Numeric, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_file import File, ImageField

from db.base import Model


class User(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    first_name: Mapped[str] = mapped_column(String(30), nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False)
    gender: Mapped[str] = mapped_column(String(15), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    dob: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "gender IN ('male', 'femail', 'other')",
            name='user_gender_check'
        ),
    )

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")


class Category(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    photo: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)

    parent: Mapped["Category"] = relationship("Category", remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")


class Product(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    photo: Mapped[File] = mapped_column(ImageField(upload_storage="default", thumbnail_size=(128, 128)))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")
    basket_items: Mapped[list["Basket"]] = relationship("Basket", back_populates="product")

    __table_args__ = (
        CheckConstraint(
            "price >= 0",
            name='product_price_check'
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name='product_stock_quantity_check'
        ),
    )


class Basket(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="basket_items")

    __table_args__ = (
        UniqueConstraint(
            "telegram_id",
            "product_id",
            name="basket_telegram_product_unique",
        ),
        CheckConstraint(
            "quantity > 0",
            name="basket_quantity_check"
        ),
    )


class Order(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order")
    payment: Mapped["Payment"] = relationship("Payment", back_populates="order", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled')",
            name='order_status_check'
        ),
        CheckConstraint(
            "total_amount >= 0",
            name='order_total_amount_check'
        ),
    )


class OrderItem(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name='order_item_quantity_check'
        ),
        CheckConstraint(
            "unit_price >= 0",
            name='order_item_unit_price_check'
        ),
        CheckConstraint(
            "total_price >= 0",
            name='order_item_total_price_check'
        ),
    )


class Payment(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="payment")

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name='payment_amount_check'
        ),
        CheckConstraint(
            "method IN ('cash', 'card', 'click', 'payme')",
            name='payment_method_check'
        ),
        CheckConstraint(
            "status IN ('pending', 'paid', 'failed', 'refunded')",
            name='payment_status_check'
        ),
    )

from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from bot.buttons import MainMenu, main_menu_keyboard
from bot.i18n import t, get_user_language
from db import database
from db.models import Order, User

router = Router(name="orders")

STATUS_ICONS = {
    "pending": "⏳",
    "paid": "✅",
    "shipped": "🚚",
    "delivered": "📦",
    "cancelled": "❌",
}

STATUS_LABELS_UZ = {
    "pending": "Kutilmoqda",
    "paid": "To'langan",
    "shipped": "Yetkazilmoqda",
    "delivered": "Yetkazildi",
    "cancelled": "Bekor qilingan",
}

STATUS_LABELS_RU = {
    "pending": "Ожидание",
    "paid": "Оплачено",
    "shipped": "В пути",
    "delivered": "Доставлено",
    "cancelled": "Отменено",
}

PAYMENT_STATUS_ICONS = {
    "pending": "⏳",
    "paid": "✅",
    "failed": "❌",
    "refunded": "↩️",
}

PAYMENT_STATUS_LABELS_UZ = {
    "pending": "Kutilmoqda",
    "paid": "To'langan",
    "failed": "Muvaffaqiyatsiz",
    "refunded": "Qaytarilgan",
}

PAYMENT_STATUS_LABELS_RU = {
    "pending": "Ожидание",
    "paid": "Оплачено",
    "failed": "Не прошло",
    "refunded": "Возвращено",
}


def _format_money(value: Decimal) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _fetch_orders(telegram_id: int) -> list[Order]:
    query = (
        select(Order)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    return list(database.execute(query).scalars().all())


def _order_items_text(order: Order, max_items: int = 2) -> str:
    lines = []
    for item in order.items[:max_items]:
        product_name = item.product.name if item.product else "Mahsulot"
        lines.append(f"• {escape(product_name)} ×{item.quantity}")

    remaining_count = len(order.items) - len(lines)
    if remaining_count > 0:
        lines.append(f"+ {remaining_count} boshqa")

    return "\n  ".join(lines) if lines else "Mahsulotlar topilmadi"


def _get_status_label(status: str, lang: str) -> str:
    labels = STATUS_LABELS_UZ if lang == 'uz' else STATUS_LABELS_RU
    return labels.get(status, status)


def _get_payment_status_label(status: str, lang: str) -> str:
    labels = PAYMENT_STATUS_LABELS_UZ if lang == 'uz' else PAYMENT_STATUS_LABELS_RU
    return labels.get(status, status)


@router.message(Command(commands=["orders"]))
@router.message(F.text.in_([t('main.orders', 'uz'), t('main.orders', 'ru')]))
async def orders_handler(message: Message) -> None:
    if message.from_user is None:
        await message.answer(
            t('profile.not_found', 'uz'),
            reply_markup=main_menu_keyboard('uz'),
        )
        return

    lang = get_user_language(message.from_user.id)
    orders = _fetch_orders(message.from_user.id)
    
    if not orders:
        await message.answer(
            t('orders.empty', lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        return

    lines = ["📦 <b>" + t('main.orders', lang) + "</b>\n"]
    for order in orders:
        payment_status = order.payment.status if order.payment else "pending"
        created_at = order.created_at.strftime("%d.%m.%Y %H:%M")
        status_icon = STATUS_ICONS.get(order.status, "•")
        payment_icon = PAYMENT_STATUS_ICONS.get(payment_status, "•")
        
        order_text = (
            f"\n{status_icon} <b>Buyurtma #{order.id}</b>\n"
            f"  📅 {created_at}\n"
            f"  Status: {_get_status_label(order.status, lang)}\n"
            f"  {payment_icon} To'lov: {_get_payment_status_label(payment_status, lang)}\n"
            f"  💰 Summa: <code>{_format_money(order.total_amount)} so'm</code>\n"
            f"  Mahsulotlar:\n"
            f"  {_order_items_text(order)}"
        )
        lines.append(order_text)

    await message.answer(
        "\n".join(lines),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )

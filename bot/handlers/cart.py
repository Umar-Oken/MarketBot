from datetime import date
from decimal import Decimal
from html import escape
import logging

from aiogram import F, Router
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from sqlalchemy import delete, select

from bot.buttons import MainMenu, main_menu_keyboard
from bot.i18n import t, get_user_language
from config import settings
from db import database
from db.models import Basket, Order, OrderItem, Payment, User

router = Router(name="cart")
logger = logging.getLogger(__name__)

CANCEL_TEXT = "❌ Bekor qilish"
PAYMENT_METHODS = {
    "cash": "💵 Naqd to'lov",
    "card": "💳 Karta orqali",
    "click": "Click",
    "payme": "Payme",
}


class Checkout(StatesGroup):
    waiting_full_name = State()
    waiting_phone = State()
    waiting_shipping_address = State()
    waiting_payment_method = State()


class CheckoutError(Exception):
    pass


def _format_money(value: Decimal) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _short_text(value: str, max_length: int = 52) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length - 1]}..."


def _fetch_basket_items(telegram_id: int) -> list[Basket]:
    query = select(Basket).where(Basket.telegram_id == telegram_id).order_by(Basket.id)
    return list(database.execute(query).scalars().all())


async def _send_callback_message(
        callback_query: CallbackQuery,
        text: str,
        reply_markup=None,
        parse_mode: str | None = None,
) -> None:
    chat_id = callback_query.from_user.id
    if callback_query.message is not None:
        chat_id = callback_query.message.chat.id

    await callback_query.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )


def _cart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Buyurtmani rasmiylashtirish",
                    callback_data="cart:checkout",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Kataloggaqa qaytish",
                    callback_data="cart:back_catalog",
                ),
                InlineKeyboardButton(
                    text="🧹 Tozalash",
                    callback_data="cart:clear",
                )
            ],
        ]
    )


def _cart_items_keyboard(items: list[Basket]) -> InlineKeyboardMarkup:
    inline_keyboard = []
    for item in items:
        product_name = _short_text(item.product.name, 28)
        price = _format_money(item.product.price)
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📦 {product_name} ({price})",
                    callback_data=f"cart:noop",
                ),
            ]
        )
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=f"cart:dec:{item.id}",
                ),
                InlineKeyboardButton(
                    text=f"{item.quantity}",
                    callback_data=f"cart:noop",
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=f"cart:inc:{item.id}",
                ),
                InlineKeyboardButton(
                    text="🗑️",
                    callback_data=f"cart:remove:{item.id}",
                ),
            ]
        )
    
    inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="✅ Buyurtmani rasmiylashtirish",
                callback_data="cart:checkout",
            )
        ]
    )
    inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="🛒 Yana sotib olish",
                callback_data="cart:continue_shopping",
            ),
            InlineKeyboardButton(
                text="🧹 Tozalash",
                callback_data="cart:clear",
            )
        ]
    )
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def _cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        input_field_placeholder="Bekor qilish uchun tugmani bosing",
    )


def _phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Telefon raqamingiz",
    )


def _payment_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    payment_methods = {
        "cash": ("💵 Naqd to'lov", "cash") if lang == "uz" else ("💵 Наличные", "cash"),
        "card": ("💳 Karta orqali", "card") if lang == "uz" else ("💳 Карта", "card"),
        "click": ("Click", "click"),
        "payme": ("Payme", "payme"),
    }
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"checkout:pay:{method}",
                )
            ]
            for label, method in payment_methods.values()
        ] + [
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="checkout:cancel")]
        ]
    )


def _basket_summary(items: list[Basket], lang: str = "uz") -> tuple[str, Decimal]:
    lines = ["🛒 <b>" + ("Savat" if lang == "uz" else "Корзина") + "</b>\n"]
    total = Decimal("0")

    for idx, item in enumerate(items, 1):
        product = item.product
        item_total = product.price * item.quantity
        total += item_total
        lines.append(
            f"\n{idx}️⃣ <b>{escape(product.name)}</b>\n"
            f"   💰 {_format_money(product.price)} so'm × {item.quantity} = "
            f"<code>{_format_money(item_total)} so'm</code>"
        )

    lines.append(f"\n\n{'─' * 35}\n💰 <b>Jami:</b> <code>{_format_money(total)} so'm</code>")
    return "\n".join(lines), total


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)
    first_name = parts[0][:30]
    last_name = parts[1][:30] if len(parts) > 1 else "-"
    return first_name, last_name


def _normalize_phone(value: str) -> str:
    phone = value.strip().replace(" ", "")
    digits = "".join(char for char in phone if char.isdigit())
    if len(digits) < 7:
        raise CheckoutError("Telefon raqam noto'g'ri kiritildi.")
    return phone[:30]


def _phone_conflict_exists(phone: str, telegram_id: int) -> bool:
    phone_owner = database.execute(
        select(User).where(User.phone == phone)
    ).scalars().first()
    if phone_owner is None:
        return False
    if phone_owner.telegram_id == telegram_id:
        return False

    current_user = database.execute(
        select(User).where(User.telegram_id == telegram_id)
    ).scalars().first()
    if current_user is not None and current_user.id != phone_owner.id:
        return True

    return phone_owner.telegram_id is not None


def _checkout_email(telegram_id: int) -> str:
    return f"telegram_{telegram_id}@marketbot.local"


def _get_or_create_user(
        telegram_id: int,
        first_name: str,
        last_name: str,
        phone: str,
) -> User:
    user = database.execute(
        select(User).where(User.telegram_id == telegram_id)
    ).scalars().first()
    phone_owner = database.execute(
        select(User).where(User.phone == phone)
    ).scalars().first()

    if user is not None and phone_owner is not None and user.id != phone_owner.id:
        raise CheckoutError("Bu telefon raqam boshqa profilga biriktirilgan.")

    if phone_owner is not None and phone_owner.telegram_id not in (None, telegram_id):
        raise CheckoutError("Bu telefon raqam boshqa profilga biriktirilgan.")

    if user is None:
        user = phone_owner

    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            gender="other",
            phone=phone,
            email=_checkout_email(telegram_id),
            dob=date(1970, 1, 1),
        )
        database.add(user)
    else:
        user.telegram_id = telegram_id
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        if not user.gender:
            user.gender = "other"
        if not user.email:
            user.email = _checkout_email(telegram_id)
        if not user.dob:
            user.dob = date(1970, 1, 1)

    return user


def _create_order_from_basket(telegram_id: int, checkout_data: dict) -> Order:
    items = _fetch_basket_items(telegram_id)
    if not items:
        raise CheckoutError("Savat hozircha bo'sh.")

    total = Decimal("0")
    for item in items:
        product = item.product
        if product is None or not product.is_active:
            raise CheckoutError("Savatdagi mahsulotlardan biri hozir mavjud emas.")
        if item.quantity > product.stock_quantity:
            raise CheckoutError(
                f"{product.name} uchun omborda faqat {product.stock_quantity} dona bor."
            )
        total += product.price * item.quantity

    try:
        user = _get_or_create_user(
            telegram_id=telegram_id,
            first_name=checkout_data["first_name"],
            last_name=checkout_data["last_name"],
            phone=checkout_data["phone"],
        )
        order = Order(
            user=user,
            total_amount=total,
            shipping_address=checkout_data["shipping_address"],
        )
        database.add(order)
        database.flush()

        for item in items:
            product = item.product
            item_total = product.price * item.quantity
            database.add(
                OrderItem(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    unit_price=product.price,
                    total_price=item_total,
                )
            )
            product.stock_quantity -= item.quantity

        database.add(
            Payment(
                order=order,
                amount=total,
                method=checkout_data["payment_method"],
                status="pending",
            )
        )

        for item in items:
            database.delete(item)

        database.commit()
    except Exception:
        database.rollback()
        raise

    return order


def _clear_basket(telegram_id: int) -> None:
    try:
        database.execute(delete(Basket).where(Basket.telegram_id == telegram_id))
        database.commit()
    except Exception:
        database.rollback()
        raise


def _order_success_text(order: Order) -> str:
    payment_method = order.payment.method if order.payment else "cash"
    return (
        f"✅ <b>Buyurtma qabul qilindi</b>\n\n"
        f"🧾 <b>Buyurtma raqami:</b> #{order.id}\n"
        f"💰 <b>Jami:</b> {_format_money(order.total_amount)} so'm\n"
        f"💳 <b>To'lov usuli:</b> {escape(PAYMENT_METHODS.get(payment_method, payment_method))}\n"
        f"📍 <b>Manzil:</b> {escape(order.shipping_address)}\n\n"
        "📞 Operator buyurtmani tasdiqlash uchun siz bilan bog'lanadi."
    )


def _admin_order_text(order: Order, telegram_id: int) -> str:
    user = order.user
    phone = user.phone if user else "-"
    full_name = f"{user.first_name} {user.last_name}".strip() if user else "-"
    payment_method = order.payment.method if order.payment else "cash"

    item_lines = []
    for index, item in enumerate(order.items, start=1):
        product_name = item.product.name if item.product else "Mahsulot"
        item_lines.append(
            f"{index}. 📦 {escape(product_name)}\n"
            f"   🔢 {item.quantity} x {_format_money(item.unit_price)} so'm = "
            f"{_format_money(item.total_price)} so'm"
        )

    return (
        f"🆕 <b>Yangi buyurtma</b>\n\n"
        f"🧾 <b>Buyurtma:</b> #{order.id}\n"
        f"👤 <b>Mijoz:</b> {escape(full_name)}\n"
        f"🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>\n"
        f"📞 <b>Telefon:</b> {escape(phone)}\n"
        f"📍 <b>Manzil:</b> {escape(order.shipping_address)}\n"
        f"💳 <b>To'lov:</b> {escape(PAYMENT_METHODS.get(payment_method, payment_method))}\n"
        f"💰 <b>Jami:</b> {_format_money(order.total_amount)} so'm\n\n"
        f"<b>Mahsulotlar:</b>\n" + "\n".join(item_lines)
    )


async def _notify_admins(bot: Bot, order: Order, telegram_id: int) -> None:
    if not settings.admin_ids:
        logger.warning("Order %s accepted, but no admin IDs are configured.", order.id)
        return

    text = _admin_order_text(order, telegram_id)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
            )
        except TelegramAPIError as error:
            logger.warning("Could not notify admin %s about order %s: %s", admin_id, order.id, error)


@router.message(Command(commands=["cart"]))
@router.message(F.text.in_([t('main.cart','uz'), t('main.cart','ru')]))
async def cart_handler(message: Message) -> None:
    if message.from_user is None:
        await message.answer(
            t('profile.not_found', 'uz'),
            reply_markup=main_menu_keyboard('uz'),
        )
        return

    lang = get_user_language(message.from_user.id)
    items = _fetch_basket_items(message.from_user.id)
    if not items:
        await message.answer(
            "🛒 " + t('main.cart', lang) + "\n\n" + t('orders.empty', lang),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    text, _ = _basket_summary(items)

    await message.answer(
        text,
        reply_markup=_cart_items_keyboard(items),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cart:clear")
async def clear_cart_handler(callback_query: CallbackQuery) -> None:
    if callback_query.from_user is None:
        await callback_query.answer("Foydalanuvchi aniqlanmadi.", show_alert=True)
        return

    _clear_basket(callback_query.from_user.id)
    if callback_query.message is not None:
        await callback_query.message.edit_text("🧹 Savat tozalandi.")
    await callback_query.answer("Savat tozalandi.")


@router.callback_query(F.data == "cart:checkout")
async def checkout_start_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.from_user is None:
        await callback_query.answer("Foydalanuvchi aniqlanmadi.", show_alert=True)
        return

    items = _fetch_basket_items(callback_query.from_user.id)
    if not items:
        await callback_query.answer("Savat hozircha bo'sh.", show_alert=True)
        return

    existing_user = database.execute(
        select(User).where(User.telegram_id == callback_query.from_user.id)
    ).scalars().first()

    await state.clear()

    if existing_user is not None:
        await state.update_data(
            first_name=existing_user.first_name,
            last_name=existing_user.last_name,
            phone=existing_user.phone,
        )
        await state.set_state(Checkout.waiting_shipping_address)
        await _send_callback_message(
            callback_query,
            "📍 Yetkazib berish manzilini kiriting.",
            reply_markup=_cancel_keyboard(),
        )
    else:
        await state.set_state(Checkout.waiting_full_name)
        await _send_callback_message(
            callback_query,
            "👤 Buyurtmani rasmiylashtirish uchun ism va familiyangizni kiriting.",
            reply_markup=_cancel_keyboard(),
        )
    await callback_query.answer()


@router.message(
    StateFilter(
        Checkout.waiting_full_name,
        Checkout.waiting_phone,
        Checkout.waiting_shipping_address,
    ),
    F.text == CANCEL_TEXT,
)
async def checkout_cancel_message_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    await message.answer(
        "❌ Buyurtma rasmiylashtirish bekor qilindi.",
        reply_markup=main_menu_keyboard(lang),
    )


@router.callback_query(F.data == "checkout:cancel")
async def checkout_cancel_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_language(callback_query.from_user.id) if callback_query.from_user else 'uz'
    await _send_callback_message(
        callback_query,
        "❌ Buyurtma rasmiylashtirish bekor qilindi.",
        reply_markup=main_menu_keyboard(lang),
    )
    await callback_query.answer()


@router.message(Checkout.waiting_full_name)
async def checkout_full_name_handler(message: Message, state: FSMContext) -> None:
    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer("👤 Ism va familiyani to'liqroq kiriting.")
        return

    first_name, last_name = _split_full_name(full_name)
    await state.update_data(first_name=first_name, last_name=last_name)
    await state.set_state(Checkout.waiting_phone)
    await message.answer(
        "📞 Telefon raqamingizni yuboring yoki matn ko'rinishida kiriting.",
        reply_markup=_phone_keyboard(),
    )


@router.message(Checkout.waiting_phone)
async def checkout_phone_handler(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        await message.answer("Foydalanuvchi aniqlanmadi.")
        return

    raw_phone = message.contact.phone_number if message.contact else message.text
    if not raw_phone:
        await message.answer("Telefon raqamni yuboring.")
        return

    try:
        phone = _normalize_phone(raw_phone)
    except CheckoutError as error:
        await message.answer(str(error))
        return

    if _phone_conflict_exists(phone, message.from_user.id):
        await message.answer("Bu telefon raqam boshqa profilga biriktirilgan. Boshqa raqam kiriting.")
        return

    await state.update_data(phone=phone)
    await state.set_state(Checkout.waiting_shipping_address)
    await message.answer(
        "📍 Yetkazib berish manzilini kiriting.",
        reply_markup=_cancel_keyboard(),
    )


@router.message(Checkout.waiting_shipping_address)
async def checkout_shipping_address_handler(message: Message, state: FSMContext) -> None:
    address = (message.text or "").strip()
    if len(address) < 5:
        await message.answer("📍 Manzilni to'liqroq kiriting.")
        return

    await state.update_data(shipping_address=address)
    await state.set_state(Checkout.waiting_payment_method)
    await message.answer(
        "💳 To'lov usulini tanlang.",
        reply_markup=_payment_keyboard(),
    )


@router.callback_query(
    StateFilter(Checkout.waiting_payment_method),
    F.data.startswith("checkout:pay:"),
)
async def checkout_payment_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.from_user is None:
        await callback_query.answer("Foydalanuvchi aniqlanmadi.", show_alert=True)
        return

    method = callback_query.data.rsplit(":", maxsplit=1)[-1]
    if method not in PAYMENT_METHODS:
        await callback_query.answer("To'lov usuli topilmadi.", show_alert=True)
        return

    checkout_data = await state.get_data()
    checkout_data["payment_method"] = method

    try:
        order = _create_order_from_basket(callback_query.from_user.id, checkout_data)
    except CheckoutError as error:
        lang = get_user_language(callback_query.from_user.id) if callback_query.from_user else 'uz'
        await _send_callback_message(
            callback_query,
            str(error),
            reply_markup=main_menu_keyboard(lang),
        )
        await state.clear()
        await callback_query.answer()
        return

    await state.clear()
    lang = get_user_language(callback_query.from_user.id) if callback_query.from_user else 'uz'
    await _send_callback_message(
        callback_query,
        _order_success_text(order),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )
    await _notify_admins(callback_query.bot, order, callback_query.from_user.id)
    await callback_query.answer("Buyurtma qabul qilindi.")


@router.callback_query(F.data.startswith("cart:inc:"))
async def cart_increment_handler(callback_query: CallbackQuery) -> None:
    if callback_query.from_user is None:
        await callback_query.answer("Foydalanuvchi aniqlanmadi.", show_alert=True)
        return

    try:
        basket_id = int(callback_query.data.split(":")[-1])
    except ValueError:
        await callback_query.answer("Xato ro'yxat ID.", show_alert=True)
        return

    try:
        item = database.execute(select(Basket).where(Basket.id == basket_id)).scalars().first()
        if item is None or item.telegram_id != callback_query.from_user.id:
            await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
            return

        product = item.product
        if item.quantity >= product.stock_quantity:
            await callback_query.answer(f"Omborda faqat {product.stock_quantity} dona bor.", show_alert=True)
            return

        item.quantity += 1
        database.commit()

        items = _fetch_basket_items(callback_query.from_user.id)
        text, _ = _basket_summary(items)

        if callback_query.message is not None:
            await callback_query.message.edit_text(
                text,
                reply_markup=_cart_items_keyboard(items),
                parse_mode="HTML",
            )
        await callback_query.answer("✅ Miqdor oshirildi.")
    except Exception as e:
        logger.error(f"Error incrementing cart item: {e}")
        await callback_query.answer("Xato yuz berdi.", show_alert=True)


@router.callback_query(F.data.startswith("cart:dec:"))
async def cart_decrement_handler(callback_query: CallbackQuery) -> None:
    if callback_query.from_user is None:
        await callback_query.answer("Foydalanuvchi aniqlanmadi.", show_alert=True)
        return

    try:
        basket_id = int(callback_query.data.split(":")[-1])
    except ValueError:
        await callback_query.answer("Xato ro'yxat ID.", show_alert=True)
        return

    try:
        item = database.execute(select(Basket).where(Basket.id == basket_id)).scalars().first()
        if item is None or item.telegram_id != callback_query.from_user.id:
            await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
            return

        if item.quantity <= 1:
            database.delete(item)
            database.commit()
            await callback_query.answer("❌ Mahsulot savatdan olib tashlandi.")

            items = _fetch_basket_items(callback_query.from_user.id)
            if not items:
                if callback_query.message is not None:
                    await callback_query.message.edit_text(
                        "🛒 Savat hozircha bo'sh.",
                        reply_markup=None,
                    )
                return

            text, _ = _basket_summary(items)
            if callback_query.message is not None:
                await callback_query.message.edit_text(
                    text,
                    reply_markup=_cart_items_keyboard(items),
                    parse_mode="HTML",
                )
        else:
            item.quantity -= 1
            database.commit()

            items = _fetch_basket_items(callback_query.from_user.id)
            text, _ = _basket_summary(items)

            if callback_query.message is not None:
                await callback_query.message.edit_text(
                    text,
                    reply_markup=_cart_items_keyboard(items),
                    parse_mode="HTML",
                )
            await callback_query.answer("✅ Miqdor kamaytrildi.")
    except Exception as e:
        logger.error(f"Error decrementing cart item: {e}")
        await callback_query.answer("Xato yuz berdi.", show_alert=True)


@router.callback_query(F.data == "cart:noop")
async def cart_noop_handler(callback_query: CallbackQuery) -> None:
    await callback_query.answer()

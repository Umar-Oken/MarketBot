from collections import defaultdict
from decimal import Decimal
from html import escape
import logging
from math import ceil
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    Message,
    ReplyKeyboardRemove,
)
from sqlalchemy import and_, or_, select

from bot.buttons import MainMenu, main_menu_keyboard
from bot.i18n import t, get_user_language
from config import settings
from db import database
from db.models import Basket, Category, Product
from db.product_photos import product_photo_public_path, product_photo_source


MAIN_MENU_TEXTS = {
    t('main.catalog','uz'),
    t('main.catalog','ru'),
    t('main.cart','uz'),
    t('main.cart','ru'),
    t('main.orders','uz'),
    t('main.orders','ru'),
    t('main.search','uz'),
    t('main.search','ru'),
    t('main.profile','uz'),
    t('main.profile','ru'),
    t('main.contact','uz'),
    t('main.contact','ru'),
    t('main.settings','uz'),
    t('main.settings','ru'),
}

router = Router(name="catalog")
logger = logging.getLogger(__name__)

CATEGORY_PAGE_SIZE = 8
PRODUCT_PAGE_SIZE = 7
SEARCH_RESULT_LIMIT = 8
INLINE_RESULT_LIMIT = 20
MAX_PRODUCT_BUTTON_TEXT_LENGTH = 52
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEARCH_CANCEL_TEXT = "❌ Bekor qilish"


class ProductSearch(StatesGroup):
    waiting_query = State()


def _format_money(value: Decimal) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _short_text(value: str, max_length: int = MAX_PRODUCT_BUTTON_TEXT_LENGTH) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length - 1]}..."


def _page_bounds(total_items: int, page_size: int, page: int) -> tuple[int, int]:
    total_pages = max(ceil(total_items / page_size), 1)
    page = max(0, min(page, total_pages - 1))
    return page, total_pages


def _fetch_categories() -> list[Category]:
    query = select(Category).order_by(Category.name)
    return list(database.execute(query).scalars().all())


def _fetch_category(category_id: int) -> Category | None:
    query = select(Category).where(Category.id == category_id)
    return database.execute(query).scalars().first()


def _fetch_product(product_id: int) -> Product | None:
    query = select(Product).where(Product.id == product_id)
    return database.execute(query).scalars().first()


def _category_ids_with_descendants(category_id: int) -> list[int]:
    rows = database.execute(select(Category.id, Category.parent_id)).all()
    children_by_parent: dict[int | None, list[int]] = defaultdict(list)

    for row in rows:
        children_by_parent[row.parent_id].append(row.id)

    category_ids = []
    stack = [category_id]
    while stack:
        current_id = stack.pop()
        category_ids.append(current_id)
        stack.extend(children_by_parent.get(current_id, []))

    return category_ids


def _fetch_products_for_category(category_id: int) -> list[Product]:
    category_ids = _category_ids_with_descendants(category_id)
    query = (
        select(Product)
        .where(Product.is_active.is_(True), Product.category_id.in_(category_ids))
        .order_by(Product.name)
    )
    return list(database.execute(query).scalars().all())


def _search_products(search_text: str, limit: int = SEARCH_RESULT_LIMIT) -> list[Product]:
    terms = [term for term in search_text.strip().split() if term]
    if not terms:
        return []

    fields = (
        Product.name,
        Product.description,
        Category.name,
        Category.description,
    )
    phrase_pattern = f"%{search_text.strip()}%"
    phrase_condition = or_(*(field.ilike(phrase_pattern) for field in fields))
    term_conditions = [
        or_(*(field.ilike(f"%{term}%") for field in fields))
        for term in terms
    ]

    query = (
        select(Product)
        .join(Category)
        .where(
            Product.is_active.is_(True),
            or_(phrase_condition, and_(*term_conditions)),
        )
        .order_by(Product.name)
        .limit(limit)
    )
    return list(database.execute(query).scalars().all())


def _fetch_inline_suggestions(limit: int = INLINE_RESULT_LIMIT) -> list[Product]:
    query = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.stock_quantity.desc(), Product.name)
        .limit(limit)
    )
    return list(database.execute(query).scalars().all())


def _categories_keyboard(categories: list[Category], page: int) -> InlineKeyboardMarkup:
    page, total_pages = _page_bounds(len(categories), CATEGORY_PAGE_SIZE, page)
    start = page * CATEGORY_PAGE_SIZE
    page_items = categories[start:start + CATEGORY_PAGE_SIZE]

    rows = [
        [
            InlineKeyboardButton(
                text=f"📂 {category.name}",
                callback_data=f"pl:{category.id}:0",
            )
        ]
        for category in page_items
    ]

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"cp:{page - 1}"))
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="Oldinga ➡️", callback_data=f"cp:{page + 1}"))
        rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _products_keyboard(
        products: list[Product],
        category_id: int,
        page: int,
) -> InlineKeyboardMarkup:
    page, total_pages = _page_bounds(len(products), PRODUCT_PAGE_SIZE, page)
    start = page * PRODUCT_PAGE_SIZE
    page_items = products[start:start + PRODUCT_PAGE_SIZE]

    rows = [
        [
            InlineKeyboardButton(
                text=f"📦 {_short_text(product.name)}",
                callback_data=f"pd:{product.id}:{category_id}:{page}",
            )
        ]
        for product in page_items
    ]

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"pl:{category_id}:{page - 1}"))
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="Oldinga ➡️", callback_data=f"pl:{category_id}:{page + 1}"))
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="⬅️ Kategoriyalarga qaytish", callback_data="cp:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _product_detail_keyboard(
        product: Product,
        category_id: int,
        page: int,
        quantity: int,
) -> InlineKeyboardMarkup:
    rows = []

    if product.stock_quantity > 0:
        quantity = max(1, min(quantity, product.stock_quantity))
        rows.append(
            [
                InlineKeyboardButton(text="➖", callback_data=f"q:{product.id}:{category_id}:{page}:{quantity}:-1"),
                InlineKeyboardButton(text=str(quantity), callback_data="noop"),
                InlineKeyboardButton(text="➕", callback_data=f"q:{product.id}:{category_id}:{page}:{quantity}:1"),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Savatga qo'shish",
                    callback_data=f"add:{product.id}:{quantity}",
                )
            ]
        )
    else:
        rows.append([InlineKeyboardButton(text="❌ Omborda yo'q", callback_data="noop")])

    rows.append([InlineKeyboardButton(text="⬅️ Mahsulotlarga qaytish", callback_data=f"pl:{category_id}:{page}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _inline_product_keyboard(product: Product) -> InlineKeyboardMarkup:
    if product.stock_quantity <= 0:
        rows = [[InlineKeyboardButton(text="❌ Omborda yo'q", callback_data="noop")]]
    else:
        rows = [
            [
                InlineKeyboardButton(
                    text="✅ Savatga qo'shish",
                    callback_data=f"add:{product.id}:1",
                )
            ]
        ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _product_detail_text(product: Product) -> str:
    description = product.description or "Tavsif kiritilmagan."
    category_name = product.category.name if product.category else "Kategoriyasiz"
    stock_status = "✅ Mavjud" if product.stock_quantity > 0 else "❌ Omborda yo'q"

    return (
        f"📦 <b>{escape(product.name)}</b>\n\n"
        f"💰 <b>Narx:</b> <code>{_format_money(product.price)} so'm</code>\n"
        f"📦 <b>Omborda:</b> {product.stock_quantity} dona ({stock_status})\n"
        f"🏷 <b>Kategoriya:</b> {escape(category_name)}\n\n"
        f"📝 <b>Tavsif:</b>\n{escape(description)}"
    )


def _product_photo(product: Product) -> str | FSInputFile | None:
    photo = product_photo_source(product.photo)
    if not photo:
        return None

    if photo.startswith(("http://", "https://")):
        return photo

    photo_path = Path(photo)
    if not photo_path.is_absolute():
        photo_path = PROJECT_ROOT / photo_path

    if not photo_path.is_file():
        return None

    return FSInputFile(photo_path)


def _product_photo_url(product: Product) -> str | None:
    photo = product_photo_public_path(product.photo)
    if not photo:
        return None

    if photo.startswith(("http://", "https://")):
        return photo

    if not settings.public_base_url:
        return None

    return f"{settings.public_base_url}/{photo.lstrip('/')}"


def _inline_result_description(product: Product) -> str:
    category_name = product.category.name if product.category else "Kategoriyasiz"
    return (
        f"{category_name} | {_format_money(product.price)} so'm | "
        f"Omborda: {product.stock_quantity} dona"
    )


def _inline_product_result(product: Product) -> InlineQueryResultArticle | InlineQueryResultPhoto:
    photo_url = _product_photo_url(product)
    reply_markup = _inline_product_keyboard(product)
    text = _product_detail_text(product)
    description = _inline_result_description(product)

    if photo_url:
        return InlineQueryResultPhoto(
            id=f"product-photo-{product.id}",
            photo_url=photo_url,
            thumbnail_url=photo_url,
            title=product.name,
            description=description,
            caption=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    return InlineQueryResultArticle(
        id=f"product-article-{product.id}",
        title=product.name,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
        reply_markup=reply_markup,
    )


def _empty_inline_result(query: str) -> InlineQueryResultArticle:
    message = (
        f"🔎 <b>{escape(query)}</b> bo'yicha mahsulot topilmadi.\n\n"
        "Boshqa kalit so'z bilan qayta urinib ko'ring."
    )
    return InlineQueryResultArticle(
        id="no-results",
        title="Mahsulot topilmadi",
        description="Boshqa mahsulot nomi, kategoriya yoki kalit so'z yozing.",
        input_message_content=InputTextMessageContent(
            message_text=message,
            parse_mode="HTML",
        ),
    )


def _callback_chat_id(callback_query: CallbackQuery) -> int:
    if callback_query.message is not None:
        return callback_query.message.chat.id
    return callback_query.from_user.id


async def _replace_callback_message(
        callback_query: CallbackQuery,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        parse_mode: str | None = None,
) -> None:
    if callback_query.message is not None:
        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except TelegramBadRequest as error:
            if "message is not modified" in str(error):
                return
            try:
                await callback_query.message.delete()
            except TelegramBadRequest:
                pass

    await callback_query.bot.send_message(
        chat_id=_callback_chat_id(callback_query),
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )


def _upsert_basket_item(telegram_id: int, product: Product, quantity: int) -> int:
    quantity = max(1, quantity)
    if product.stock_quantity <= 0:
        return 0

    query = select(Basket).where(
        Basket.telegram_id == telegram_id,
        Basket.product_id == product.id,
    )
    basket_item = database.execute(query).scalars().first()

    try:
        if basket_item is None:
            basket_item = Basket(
                telegram_id=telegram_id,
                product=product,
                quantity=min(quantity, product.stock_quantity),
            )
            database.add(basket_item)
        else:
            basket_item.quantity = min(
                basket_item.quantity + quantity,
                product.stock_quantity,
            )

        database.commit()
    except Exception:
        database.rollback()
        raise

    return basket_item.quantity


def _inline_search_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Qidirishni boshlash",
                    switch_inline_query_current_chat="",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="search:cancel",
                )
            ],
        ]
    )


async def _send_categories(message: Message, page: int = 0) -> None:
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    categories = _fetch_categories()
    if not categories:
        await message.answer(
            "📭 Kategoriyalar hozircha mavjud emas.",
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await message.answer(
        "🛍️ <b>Kategoriya Tanlang</b>\n\nQuyidagi kategoriyalardan birini tanlang 👇",
        reply_markup=_categories_keyboard(categories, page),
        parse_mode="HTML",
    )


async def _edit_categories(callback_query: CallbackQuery, page: int = 0) -> None:
    categories = _fetch_categories()
    if not categories:
        await _replace_callback_message(callback_query, "📭 Kategoriyalar hozircha mavjud emas.")
        await callback_query.answer()
        return

    await _replace_callback_message(
        callback_query,
        "🛍️ <b>Kategoriya Tanlang</b>\n\nQuyidagi kategoriyalardan birini tanlang 👇",
        reply_markup=_categories_keyboard(categories, page),
    )
    await callback_query.answer()


async def _edit_products(callback_query: CallbackQuery, category_id: int, page: int = 0) -> None:
    category = _fetch_category(category_id)
    if category is None:
        await callback_query.answer("❌ Kategoriya topilmadi.", show_alert=True)
        return

    products = _fetch_products_for_category(category_id)
    if not products:
        await _replace_callback_message(
            callback_query,
            f"📂 <b>{escape(category.name)}</b>\n\n📭 Bu kategoriyada hozircha mahsulot yo'q.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Kategoriyalarga qaytish", callback_data="cp:0")]
                ]
            ),
            parse_mode="HTML",
        )
        await callback_query.answer()
        return

    page, total_pages = _page_bounds(len(products), PRODUCT_PAGE_SIZE, page)
    await _replace_callback_message(
        callback_query,
        f"📂 <b>{escape(category.name)}</b>\n"
        f"📦 Mahsulotlar: {len(products)} ta\n"
        f"📄 Sahifa: {page + 1}/{total_pages}\n\n"
        "👇 Mahsulotni tanlang:",
        reply_markup=_products_keyboard(products, category_id, page),
        parse_mode="HTML",
    )
    await callback_query.answer()


async def _edit_product_detail(
        callback_query: CallbackQuery,
        product_id: int,
        category_id: int,
        page: int,
        quantity: int = 1,
) -> None:
    product = _fetch_product(product_id)
    if product is None:
        await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
        return

    text = _product_detail_text(product)
    reply_markup = _product_detail_keyboard(product, category_id, page, quantity)
    photo = _product_photo(product)

    if photo is None:
        await _replace_callback_message(
            callback_query,
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        await callback_query.answer()
        return

    if callback_query.message is not None:
        try:
            await callback_query.message.delete()
        except TelegramBadRequest:
            pass

    try:
        await callback_query.bot.send_photo(
            chat_id=_callback_chat_id(callback_query),
            photo=photo,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        await callback_query.bot.send_message(
            chat_id=_callback_chat_id(callback_query),
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    await callback_query.answer()


@router.inline_query()
async def inline_product_search_handler(inline_query: InlineQuery) -> None:
    query = inline_query.query.strip()
    if query:
        products = _search_products(query, limit=INLINE_RESULT_LIMIT)
    else:
        products = _fetch_inline_suggestions()

    results = [_inline_product_result(product) for product in products]
    if query and not results:
        results = [_empty_inline_result(query)]

    await inline_query.answer(
        results=results,
        cache_time=1,
        is_personal=True,
    )


@router.message(Command(commands=["catalog"]))
@router.message(F.text == MainMenu.CATALOG)
async def catalog_handler(message: Message) -> None:
    await _send_categories(message)


@router.message(Command(commands=["search"]))
@router.message(F.text == MainMenu.SEARCH)
async def search_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ProductSearch.waiting_query)
    await message.answer(
        "🔎 Qidirish rejimi yoqildi.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "🔎 <b>Qidirish</b>\n\n"
        "Inline qidiruv uchun tugmani bosing yoki shu yerga mahsulot nomi, "
        "kategoriya yoki kalit so'z yozing.\n"
        "Masalan: <i>iphone</i>, <i>noutbuk</i>, <i>audio</i>, <i>samsung</i>.",
        reply_markup=_inline_search_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "search:cancel")
async def search_cancel_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_language(callback_query.from_user.id) if callback_query.from_user else 'uz'
    if callback_query.message is not None:
        await callback_query.message.edit_text("❌ Qidirish bekor qilindi.")
        await callback_query.message.answer(
            "👇 Asosiy menyu:",
            reply_markup=main_menu_keyboard(lang),
        )
    await callback_query.answer()


@router.message(StateFilter(ProductSearch.waiting_query), F.text == SEARCH_CANCEL_TEXT)
async def search_cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    await message.answer(
        "❌ Qidirish bekor qilindi.",
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(StateFilter(ProductSearch.waiting_query), F.text.in_(MAIN_MENU_TEXTS))
async def search_menu_button_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    await message.answer(
        "🔎 Qidirish rejimi yopildi. Kerakli bo'limni menyudan qayta tanlang.",
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(ProductSearch.waiting_query)
async def search_query_handler(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("🔎 Kamida 2 ta belgi kiriting.")
        return

    products = _search_products(query)
    if not products:
        await message.answer(
            f"🔎 <b>{escape(query)}</b> bo'yicha mahsulot topilmadi.\n\n"
            "Boshqa kalit so'z bilan qayta urinib ko'ring.",
            parse_mode="HTML",
        )
        return

    await state.clear()
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    await message.answer(
        f"🔎 <b>{escape(query)}</b> bo'yicha {len(products)} ta mahsulot topildi:",
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )

    for product in products:
        reply_markup = _product_detail_keyboard(
            product=product,
            category_id=product.category_id,
            page=0,
            quantity=1,
        )
        text = _product_detail_text(product)
        photo = _product_photo(product)

        if photo is None:
            await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            continue

        try:
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )


@router.callback_query(F.data == "noop")
async def noop_handler(callback_query: CallbackQuery) -> None:
    await callback_query.answer()


@router.callback_query(F.data.startswith("cp:"))
async def category_page_handler(callback_query: CallbackQuery) -> None:
    _, page = callback_query.data.split(":")
    await _edit_categories(callback_query, int(page))


@router.callback_query(F.data.startswith("pl:"))
async def product_list_handler(callback_query: CallbackQuery) -> None:
    _, category_id, page = callback_query.data.split(":")
    await _edit_products(callback_query, int(category_id), int(page))


@router.callback_query(F.data.startswith("pd:"))
async def product_detail_handler(callback_query: CallbackQuery) -> None:
    _, product_id, category_id, page = callback_query.data.split(":")
    await _edit_product_detail(
        callback_query,
        product_id=int(product_id),
        category_id=int(category_id),
        page=int(page),
    )


@router.callback_query(F.data.startswith("q:"))
async def product_quantity_handler(callback_query: CallbackQuery) -> None:
    _, product_id, category_id, page, quantity, delta = callback_query.data.split(":")
    product = _fetch_product(int(product_id))
    if product is None:
        await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
        return

    old_quantity = int(quantity)
    new_quantity = max(1, min(old_quantity + int(delta), product.stock_quantity))
    if new_quantity == old_quantity:
        await callback_query.answer("Miqdor chegarasiga yetdi.")
        return

    await _edit_product_detail(
        callback_query,
        product_id=product.id,
        category_id=int(category_id),
        page=int(page),
        quantity=new_quantity,
    )


@router.callback_query(F.data.startswith("add:"))
async def add_to_basket_handler(callback_query: CallbackQuery) -> None:
    if callback_query.from_user is None:
        await callback_query.answer("Foydalanuvchi aniqlanmadi.", show_alert=True)
        return

    try:
        _, product_id, quantity = callback_query.data.split(":")
        product_id = int(product_id)
        quantity = int(quantity)
    except (TypeError, ValueError):
        await callback_query.answer("Savatga qo'shish so'rovi noto'g'ri.", show_alert=True)
        return

    product = _fetch_product(product_id)
    if product is None:
        await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
        return

    try:
        saved_quantity = _upsert_basket_item(
            telegram_id=callback_query.from_user.id,
            product=product,
            quantity=quantity,
        )
    except Exception:
        logger.exception(
            "Could not add product %s to basket for telegram_id %s",
            product.id,
            callback_query.from_user.id,
        )
        await callback_query.answer("Mahsulot savatga qo'shilmadi. Qayta urinib ko'ring.", show_alert=True)
        return

    if saved_quantity == 0:
        await callback_query.answer("Bu mahsulot hozir omborda yo'q.", show_alert=True)
        return

    await callback_query.answer(
        f"🛒 Savatga qo'shildi.\nSavatda: {saved_quantity} dona.",
        show_alert=True,
    )
    if callback_query.message is not None and callback_query.message.chat.id == callback_query.from_user.id:
        lang = get_user_language(callback_query.from_user.id) if callback_query.from_user else 'uz'
        await callback_query.message.answer(
            f"✅ {escape(product.name)} savatga qo'shildi.\n"
            f"🛒 Savatdagi miqdor: {saved_quantity} dona.",
            reply_markup=main_menu_keyboard(lang),
        )

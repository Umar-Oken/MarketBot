from decimal import Decimal
from html import escape
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from bot.admin.filters import IsAdmin
from bot.admin.buttons import admin_main_menu_keyboard, admin_back_keyboard, product_actions_keyboard
from db import database
from db.models import Product, Category

router = Router(name="admin_products")


class ProductState(StatesGroup):
    waiting_category = State()
    waiting_name = State()
    waiting_price = State()
    waiting_stock = State()
    waiting_description = State()


@router.callback_query(IsAdmin(), F.data == "admin:product:add")
async def add_product_start(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Start adding a new product."""
    categories = database.execute(select(Category)).scalars().all()
    
    if not categories:
        await callback_query.answer("Kategoriyalar topilmadi. Avval kategoriya qo'shing.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=cat.name,
            callback_data=f"admin:product:add:category:{cat.id}"
        )]
        for cat in categories
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "📦 <b>Yangi Mahsulot Qo'shish</b>\n\n"
        "Mahsulot kategoriyasini tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:product:add:category:"))
async def product_category_selected(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Handle category selection."""
    category_id = int(callback_query.data.split(":")[-1])
    
    await state.set_state(ProductState.waiting_name)
    await state.update_data(category_id=category_id)
    
    await callback_query.message.edit_text(
        "📝 Mahsulot nomini kiriting 👇",
        parse_mode="HTML",
        reply_markup=None,
    )
    await callback_query.answer()


@router.message(IsAdmin(), StateFilter(ProductState.waiting_name))
async def product_name_input(message: Message, state: FSMContext) -> None:
    """Get product name."""
    name = message.text.strip()
    
    if not name or len(name) > 150:
        await message.answer(
            "❌ Mahsulot nomi 1-150 ta belgidan iborat bo'lishi kerak.",
            reply_markup=admin_back_keyboard(),
        )
        return
    
    await state.update_data(name=name)
    await message.answer(
        "💰 Mahsulot narxini kiriting (raqam) 👇",
        reply_markup=admin_back_keyboard(),
    )
    await state.set_state(ProductState.waiting_price)


@router.message(IsAdmin(), StateFilter(ProductState.waiting_price))
async def product_price_input(message: Message, state: FSMContext) -> None:
    """Get product price."""
    try:
        price = Decimal(message.text.strip())
        if price < 0:
            raise ValueError("Narx manfiy bo'lishi mumkin emas")
        
        await state.update_data(price=price)
        await message.answer(
            "📦 Mahsulot miqdorini kiriting (raqam) 👇",
            reply_markup=admin_back_keyboard(),
        )
        await state.set_state(ProductState.waiting_stock)
    except Exception:
        await message.answer(
            "❌ Iltimos, to'g'ri raqam kiriting.",
            reply_markup=admin_back_keyboard(),
        )


@router.message(IsAdmin(), StateFilter(ProductState.waiting_stock))
async def product_stock_input(message: Message, state: FSMContext) -> None:
    """Get product stock."""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Miqdor manfiy bo'lishi mumkin emas")
        
        await state.update_data(stock_quantity=stock)
        await message.answer(
            "📝 Mahsulot tavsifini kiriting (ixtiyoriy):\n\n"
            "Yoki <code>skip</code> deb yozing.",
            parse_mode="HTML",
            reply_markup=admin_back_keyboard(),
        )
        await state.set_state(ProductState.waiting_description)
    except Exception:
        await message.answer(
            "❌ Iltimos, to'g'ri raqam kiriting.",
            reply_markup=admin_back_keyboard(),
        )


@router.message(IsAdmin(), StateFilter(ProductState.waiting_description))
async def product_description_input(message: Message, state: FSMContext) -> None:
    """Get product description and create product."""
    description = message.text.strip() if message.text.lower() != "skip" else None
    
    data = await state.get_data()
    
    try:
        new_product = Product(
            category_id=data.get("category_id"),
            name=data.get("name"),
            price=data.get("price"),
            stock_quantity=data.get("stock_quantity"),
            description=description,
            is_active=True
        )
        database.add(new_product)
        database.commit()
        
        await message.answer(
            f"✅ <b>Mahsulot Qo'shildi</b>\n\n"
            f"📦 Nomi: {escape(data.get('name'))}\n"
            f"💰 Narxi: {data.get('price')} so'm\n"
            f"📊 Miqdori: {data.get('stock_quantity')} dona\n"
            f"📝 Tavsifi: {escape(description or 'Kiritilmagan')[:100]}",
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(
            f"❌ Xato: {str(e)}",
            reply_markup=admin_main_menu_keyboard(),
        )
    
    await state.clear()


@router.callback_query(IsAdmin(), F.data == "admin:product:list")
async def list_products(callback_query: CallbackQuery) -> None:
    """Show list of products."""
    products = database.execute(select(Product).limit(50)).scalars().all()
    
    if not products:
        await callback_query.message.edit_text(
            "📦 <b>Mahsulotlar</b>\n\n"
            "Mahsulotlar topilmadi.",
            parse_mode="HTML",
            reply_markup=product_actions_keyboard(),
        )
        await callback_query.answer()
        return
    
    lines = [f"📦 <b>Mahsulotlar ({len(products)} ta)</b>\n"]
    
    for idx, prod in enumerate(products, 1):
        status = "✅ Faol" if prod.is_active else "❌ O'chiq"
        lines.append(
            f"\n{idx}️⃣ <b>{escape(prod.name)}</b> (ID: {prod.id})\n"
            f"   💰 Narxi: {prod.price} so'm\n"
            f"   📦 Omborda: {prod.stock_quantity} dona\n"
            f"   {status}"
        )
    
    await callback_query.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=product_actions_keyboard(),
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data == "admin:product:edit")
async def edit_product_start(callback_query: CallbackQuery) -> None:
    """Start editing a product."""
    products = database.execute(select(Product).limit(20)).scalars().all()
    
    if not products:
        await callback_query.answer("Mahsulotlar topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=f"✏️ {prod.name[:30]}",
            callback_data=f"admin:product:edit:{prod.id}"
        )]
        for prod in products
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "✏️ <b>Mahsulot O'zgartirish</b>\n\n"
        "O'zgartirilacak mahsulotni tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:product:edit:"))
async def edit_product_menu(callback_query: CallbackQuery) -> None:
    """Show product edit menu."""
    product_id = int(callback_query.data.split(":")[-1])
    product = database.execute(select(Product).where(Product.id == product_id)).scalar()
    
    if not product:
        await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text="📝 Nomini O'zgartirish",
            callback_data=f"admin:product:edit:name:{product_id}"
        )],
        [InlineKeyboardButton(
            text="💰 Narxini O'zgartirish",
            callback_data=f"admin:product:edit:price:{product_id}"
        )],
        [InlineKeyboardButton(
            text="📦 Miqdorini O'zgartirish",
            callback_data=f"admin:product:edit:stock:{product_id}"
        )],
        [InlineKeyboardButton(
            text="✅ Status O'zgartirish",
            callback_data=f"admin:product:edit:status:{product_id}"
        )],
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    status = "✅ Faol" if product.is_active else "❌ O'chiq"
    await callback_query.message.edit_text(
        f"✏️ <b>{escape(product.name)}</b> Mahsulotini O'zgartirish\n\n"
        f"💰 Narxi: {product.price} so'm\n"
        f"📦 Omborda: {product.stock_quantity} dona\n"
        f"Status: {status}\n\n"
        "O'zgartirilacak qismni tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:product:edit:status:"))
async def toggle_product_status(callback_query: CallbackQuery) -> None:
    """Toggle product active status."""
    product_id = int(callback_query.data.split(":")[-1])
    
    try:
        product = database.execute(select(Product).where(Product.id == product_id)).scalar()
        if product:
            product.is_active = not product.is_active
            database.commit()
            
            status = "✅ Faol" if product.is_active else "❌ O'chiq"
            await callback_query.message.edit_text(
                f"✅ <b>Status O'zgartirildi</b>\n\n"
                f"📦 {escape(product.name)}\n"
                f"Yangi status: {status}",
                parse_mode="HTML",
                reply_markup=product_actions_keyboard(),
            )
        else:
            await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"Xato: {str(e)}", show_alert=True)
    
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data == "admin:product:delete")
async def delete_product_start(callback_query: CallbackQuery) -> None:
    """Start deleting a product."""
    products = database.execute(select(Product).limit(20)).scalars().all()
    
    if not products:
        await callback_query.answer("Mahsulotlar topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=f"🗑️ {prod.name[:30]}",
            callback_data=f"admin:product:delete:{prod.id}"
        )]
        for prod in products
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "🗑️ <b>Mahsulot O'chirish</b>\n\n"
        "O'chirilacak mahsulotni tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:product:delete:"))
async def delete_product_confirm(callback_query: CallbackQuery) -> None:
    """Confirm product deletion."""
    product_id = int(callback_query.data.split(":")[-1])
    
    try:
        product = database.execute(select(Product).where(Product.id == product_id)).scalar()
        
        if not product:
            await callback_query.answer("Mahsulot topilmadi.", show_alert=True)
            return
        
        product_name = product.name
        database.delete(product)
        database.commit()
        
        await callback_query.message.edit_text(
            f"✅ <b>Mahsulot O'chirildi</b>\n\n"
            f"📦 {escape(product_name)}",
            parse_mode="HTML",
            reply_markup=product_actions_keyboard(),
        )
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ Xato: {str(e)}",
            reply_markup=product_actions_keyboard(),
        )
    
    await callback_query.answer()

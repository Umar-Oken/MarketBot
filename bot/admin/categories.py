from html import escape
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from bot.admin.filters import IsAdmin
from bot.admin.buttons import admin_main_menu_keyboard, admin_back_keyboard, category_actions_keyboard
from db import database
from db.models import Category

router = Router(name="admin_categories")


class CategoryState(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_parent_id = State()


@router.callback_query(IsAdmin(), F.data == "admin:category:add")
async def add_category_start(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Start adding a new category."""
    await callback_query.message.edit_text(
        "📁 <b>Yangi Kategoriya Qo'shish</b>\n\n"
        "Kategoriyaning nomini kiriting 👇",
        parse_mode="HTML",
        reply_markup=None,
    )
    await callback_query.answer()
    await state.set_state(CategoryState.waiting_name)


@router.message(IsAdmin(), StateFilter(CategoryState.waiting_name))
async def add_category_name(message: Message, state: FSMContext) -> None:
    """Get category name."""
    name = message.text.strip()
    
    if not name or len(name) > 100:
        await message.answer(
            "❌ Kategoriya nomi 1-100 ta belgidan iborat bo'lishi kerak.",
            reply_markup=admin_back_keyboard(),
        )
        return
    
    await state.update_data(name=name)
    await message.answer(
        "📝 Kategoriyaning tavsifini kiriting (ixtiyoriy):\n\n"
        "Yoki <code>skip</code> deb yozing va o'tib keting.",
        parse_mode="HTML",
        reply_markup=admin_back_keyboard(),
    )
    await state.set_state(CategoryState.waiting_description)


@router.message(IsAdmin(), StateFilter(CategoryState.waiting_description))
async def add_category_description(message: Message, state: FSMContext) -> None:
    """Get category description."""
    description = message.text.strip() if message.text.lower() != "skip" else None
    
    if description and len(description) > 500:
        await message.answer(
            "❌ Tavsif 500 ta belgidan ko'p bo'lishi mumkin emas.",
            reply_markup=admin_back_keyboard(),
        )
        return
    
    data = await state.get_data()
    name = data.get("name")
    
    try:
        new_category = Category(name=name, description=description)
        database.add(new_category)
        database.commit()
        
        await message.answer(
            f"✅ <b>Kategoriya Qo'shildi</b>\n\n"
            f"📁 Nomi: {escape(name)}\n"
            f"📝 Tavsif: {escape(description or 'Kiritilmagan')}",
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(
            f"❌ Xato: {str(e)}",
            reply_markup=admin_main_menu_keyboard(),
        )
    
    await state.clear()


@router.callback_query(IsAdmin(), F.data == "admin:category:list")
async def list_categories(callback_query: CallbackQuery) -> None:
    """Show list of categories."""
    categories = database.execute(select(Category).limit(50)).scalars().all()
    
    if not categories:
        await callback_query.message.edit_text(
            "📁 <b>Kategoriyalar</b>\n\n"
            "Kategoriyalar topilmadi.",
            parse_mode="HTML",
            reply_markup=category_actions_keyboard(),
        )
        await callback_query.answer()
        return
    
    lines = [f"📁 <b>Kategoriyalar ({len(categories)} ta)</b>\n"]
    
    for idx, cat in enumerate(categories, 1):
        products_count = len(cat.products) if hasattr(cat, "products") else 0
        lines.append(
            f"\n{idx}️⃣ <b>{escape(cat.name)}</b> (ID: {cat.id})\n"
            f"   📦 Mahsulotlar: {products_count}\n"
            f"   📝 {escape(cat.description or '–')[:60]}"
        )
    
    await callback_query.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=category_actions_keyboard(),
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data == "admin:category:edit")
async def edit_category_start(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Start editing a category."""
    categories = database.execute(select(Category).limit(20)).scalars().all()
    
    if not categories:
        await callback_query.answer("Kategoriyalar topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=f"✏️ {cat.name}",
            callback_data=f"admin:category:edit:{cat.id}"
        )]
        for cat in categories
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "✏️ <b>Kategoriya O'zgartirish</b>\n\n"
        "O'zgartirilacak kategoriyani tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:category:edit:"))
async def edit_category_content(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Edit category content."""
    category_id = int(callback_query.data.split(":")[-1])
    category = database.execute(select(Category).where(Category.id == category_id)).scalar()
    
    if not category:
        await callback_query.answer("Kategoriya topilmadi.", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        f"✏️ <b>O'zgartirilayotgan Kategoriya</b>\n\n"
        f"📁 <b>Nomi:</b> {escape(category.name)}\n"
        f"📝 <b>Tavsifi:</b> {escape(category.description or '–')}\n\n"
        f"Yangi nomini kiriting:",
        parse_mode="HTML",
        reply_markup=None,
    )
    await callback_query.answer()
    await state.set_state(CategoryState.waiting_name)
    await state.update_data(category_id=category_id)


@router.message(IsAdmin(), StateFilter(CategoryState.waiting_name), F.text)
async def update_category_name(message: Message, state: FSMContext) -> None:
    """Update category name."""
    data = await state.get_data()
    category_id = data.get("category_id")
    
    if not category_id:
        await state.clear()
        return
    
    new_name = message.text.strip()
    
    try:
        category = database.execute(select(Category).where(Category.id == category_id)).scalar()
        if category:
            category.name = new_name
            database.commit()
            
            await message.answer(
                f"✅ <b>Kategoriya O'zgartirildi</b>\n\n"
                f"📁 Yangi nomi: {escape(new_name)}",
                reply_markup=admin_main_menu_keyboard(),
                parse_mode="HTML",
            )
        else:
            await message.answer("❌ Kategoriya topilmadi.", reply_markup=admin_main_menu_keyboard())
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}", reply_markup=admin_main_menu_keyboard())
    
    await state.clear()


@router.callback_query(IsAdmin(), F.data == "admin:category:delete")
async def delete_category_start(callback_query: CallbackQuery) -> None:
    """Start deleting a category."""
    categories = database.execute(select(Category).limit(20)).scalars().all()
    
    if not categories:
        await callback_query.answer("Kategoriyalar topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=f"🗑️ {cat.name}",
            callback_data=f"admin:category:delete:{cat.id}"
        )]
        for cat in categories
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "🗑️ <b>Kategoriya O'chirish</b>\n\n"
        "O'chirilacak kategoriyani tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:category:delete:"))
async def delete_category_confirm(callback_query: CallbackQuery) -> None:
    """Confirm category deletion."""
    category_id = int(callback_query.data.split(":")[-1])
    
    try:
        category = database.execute(select(Category).where(Category.id == category_id)).scalar()
        
        if not category:
            await callback_query.answer("Kategoriya topilmadi.", show_alert=True)
            return
        
        # Check if category has products
        if category.products:
            await callback_query.answer(
                f"Bunga {len(category.products)} ta mahsulot bog'langan. "
                "Avval mahsulotlarni o'chiring.",
                show_alert=True
            )
            return
        
        database.delete(category)
        database.commit()
        
        await callback_query.message.edit_text(
            f"✅ <b>Kategoriya O'chirildi</b>\n\n"
            f"📁 {escape(category.name)} kategoriyas o'chirildi.",
            parse_mode="HTML",
            reply_markup=category_actions_keyboard(),
        )
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ Xato: {str(e)}",
            reply_markup=category_actions_keyboard(),
        )
    
    await callback_query.answer()

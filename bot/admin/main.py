from aiogram import F, Router
from aiogram.types import Message

from bot.admin.buttons import admin_main_menu_keyboard
from bot.admin.filters import IsAdmin

router = Router(name="admin_main")


@router.message(IsAdmin(), F.text == "/admin")
async def admin_command_handler(message: Message) -> None:
    """Handle /admin command."""
    await message.answer(
        "🔐 <b>Admin Panel</b>\n\n"
        "Xush kelibsiz! Quyidagi bo'limlarni boshqaring 👇",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["📁 Kategoriyalar"]))
async def categories_menu_handler(message: Message) -> None:
    """Show categories management menu."""
    from bot.admin.buttons import category_actions_keyboard
    
    await message.answer(
        "📁 <b>Kategoriyalar Boshqaruvi</b>\n\n"
        "Kategoriyalar bilan ishlash uchun tugmani tanlang 👇",
        reply_markup=category_actions_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["📦 Mahsulotlar"]))
async def products_menu_handler(message: Message) -> None:
    """Show products management menu."""
    from bot.admin.buttons import product_actions_keyboard
    
    await message.answer(
        "📦 <b>Mahsulotlar Boshqaruvi</b>\n\n"
        "Mahsulotlar bilan ishlash uchun tugmani tanlang 👇",
        reply_markup=product_actions_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["👥 Foydalanuvchilar"]))
async def users_menu_handler(message: Message) -> None:
    """Show users list."""
    from sqlalchemy import select
    from db import database
    from db.models import User
    
    users = database.execute(select(User).limit(50)).scalars().all()
    
    if not users:
        await message.answer(
            "👥 <b>Foydalanuvchilar</b>\n\n"
            "Foydalanuvchilar topilmadi.",
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    
    lines = [
        "👥 <b>Foydalanuvchilar Ro'yxati</b>\n"
        f"<b>Jami:</b> {len(users)} ta\n"
    ]
    
    for user in users[:20]:
        username = f"@{user.first_name}" if user.first_name else "–"
        phone = user.phone or "–"
        lines.append(
            f"\n📱 <b>{user.first_name} {user.last_name}</b>\n"
            f"   📞 {phone}\n"
            f"   💬 {username}\n"
            f"   📅 {user.created_at.strftime('%d.%m.%Y')}"
        )
    
    if len(users) > 20:
        lines.append(f"\n... va yana {len(users) - 20} ta")
    
    await message.answer(
        "\n".join(lines),
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["📋 Buyurtmalar"]))
async def orders_menu_handler(message: Message) -> None:
    """Show orders management menu."""
    from bot.admin.buttons import order_actions_keyboard
    
    await message.answer(
        "📋 <b>Buyurtmalar Boshqaruvi</b>\n\n"
        "Buyurtmalar bilan ishlash uchun tugmani tanlang 👇",
        reply_markup=order_actions_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["📢 Xabar Yuborish"]))
async def broadcast_menu_handler(message: Message) -> None:
    """Show broadcast menu."""
    from bot.admin.buttons import admin_cancel_keyboard
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    
    class BroadcastState(StatesGroup):
        waiting_message = State()
    
    await message.answer(
        "📢 <b>Xabar Yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuborilacak xabarni kiriting 👇\n\n"
        "<i>Maslahat: HTML formatlash qo'lllanadi</i>",
        reply_markup=admin_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["📊 Statistika"]))
async def statistics_handler(message: Message) -> None:
    """Show statistics."""
    from sqlalchemy import select, func
    from db import database
    from db.models import User, Product, Order, Category
    
    total_users = database.execute(select(func.count(User.id))).scalar() or 0
    total_products = database.execute(select(func.count(Product.id))).scalar() or 0
    total_categories = database.execute(select(func.count(Category.id))).scalar() or 0
    total_orders = database.execute(select(func.count(Order.id))).scalar() or 0
    
    from decimal import Decimal
    from sqlalchemy import func as db_func
    total_sales = database.execute(
        select(db_func.sum(Order.total_amount))
    ).scalar() or Decimal("0")
    
    paid_orders = database.execute(
        select(func.count(Order.id)).where(Order.status.in_(["paid", "shipped", "delivered"]))
    ).scalar() or 0
    
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b> {total_users}\n"
        f"📦 <b>Mahsulotlar:</b> {total_products}\n"
        f"📁 <b>Kategoriyalar:</b> {total_categories}\n"
        f"📋 <b>Jami Buyurtmalar:</b> {total_orders}\n"
        f"✅ <b>To'langan Buyurtmalar:</b> {paid_orders}\n"
        f"💰 <b>Jami Sotuvlar:</b> {total_sales:,.0f} so'm",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(IsAdmin(), F.text.in_(["⬅️ Orqaga", "🏠 Bosh Menyusi"]))
async def back_to_main_menu_handler(message: Message) -> None:
    """Go back to main admin menu."""
    await message.answer(
        "🔐 <b>Admin Panel</b>\n\n"
        "Quyidagi bo'limlarni boshqaring 👇",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML",
    )

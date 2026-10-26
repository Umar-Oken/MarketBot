from html import escape
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from bot.admin.filters import IsAdmin
from bot.admin.buttons import admin_main_menu_keyboard, admin_cancel_keyboard, order_actions_keyboard, order_status_keyboard
from db import database
from db.models import Order, User

router = Router(name="admin_orders_broadcast")


class BroadcastState(StatesGroup):
    waiting_message = State()


@router.callback_query(IsAdmin(), F.data == "admin:order:list")
async def list_orders(callback_query: CallbackQuery) -> None:
    """Show list of orders."""
    orders = database.execute(select(Order).order_by(Order.created_at.desc()).limit(20)).scalars().all()
    
    if not orders:
        await callback_query.message.edit_text(
            "📋 <b>Buyurtmalar</b>\n\n"
            "Buyurtmalar topilmadi.",
            parse_mode="HTML",
            reply_markup=order_actions_keyboard(),
        )
        await callback_query.answer()
        return
    
    lines = [f"📋 <b>Buyurtmalar ({len(orders)} ta)</b>\n"]
    
    for idx, order in enumerate(orders, 1):
        status_emoji = {
            "pending": "⏳",
            "paid": "✅",
            "shipped": "🚚",
            "delivered": "📦",
            "cancelled": "❌",
        }.get(order.status, "•")
        
        lines.append(
            f"\n{idx}️⃣ <b>Buyurtma #{order.id}</b>\n"
            f"   {status_emoji} Status: {order.status}\n"
            f"   💰 Summa: {order.total_amount} so'm\n"
            f"   📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
    
    await callback_query.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=order_actions_keyboard(),
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data == "admin:order:view")
async def view_order_start(callback_query: CallbackQuery) -> None:
    """Start viewing order details."""
    orders = database.execute(select(Order).order_by(Order.created_at.desc()).limit(10)).scalars().all()
    
    if not orders:
        await callback_query.answer("Buyurtmalar topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=f"#{order.id} - {order.status}",
            callback_data=f"admin:order:view:{order.id}"
        )]
        for order in orders
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "👁️ <b>Buyurtma Tafsilotlarini Ko'rish</b>\n\n"
        "Buyurtmani tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:order:view:"))
async def view_order_details(callback_query: CallbackQuery) -> None:
    """View order details."""
    order_id = int(callback_query.data.split(":")[-1])
    order = database.execute(select(Order).where(Order.id == order_id)).scalar()
    
    if not order:
        await callback_query.answer("Buyurtma topilmadi.", show_alert=True)
        return
    
    user = order.user
    lines = [
        f"📋 <b>Buyurtma #{order.id} Tafsilotlari</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {escape(user.first_name)} {escape(user.last_name)}\n"
        f"📞 <b>Telefon:</b> {user.phone}\n"
        f"📧 <b>Email:</b> {user.email}\n"
        f"📅 <b>Sana:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"📦 <b>Buyurtma Ma'lumotlari:</b>\n"
        f"   Status: {order.status}\n"
        f"   💰 Jami: {order.total_amount} so'm\n"
        f"   📮 Manzil: {escape(order.shipping_address)}\n\n"
        f"📋 <b>Mahsulotlar:</b>\n"
    ]
    
    if order.items:
        for item in order.items:
            lines.append(
                f"   • {escape(item.product.name)} x {item.quantity} = {item.total_price} so'm"
            )
    else:
        lines.append("   (Mahsulot topilmadi)")
    
    await callback_query.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=order_actions_keyboard(),
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data == "admin:order:status")
async def update_order_status_start(callback_query: CallbackQuery) -> None:
    """Start updating order status."""
    orders = database.execute(select(Order).order_by(Order.created_at.desc()).limit(10)).scalars().all()
    
    if not orders:
        await callback_query.answer("Buyurtmalar topilmadi.", show_alert=True)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = [
        [InlineKeyboardButton(
            text=f"#{order.id} - {order.status}",
            callback_data=f"admin:order:update_status:{order.id}"
        )]
        for order in orders
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "🔄 <b>Buyurtma Statusini O'zgartirish</b>\n\n"
        "Buyurtmani tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:order:update_status:"))
async def select_new_status(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Select new status for order."""
    order_id = int(callback_query.data.split(":")[-1])
    order = database.execute(select(Order).where(Order.id == order_id)).scalar()
    
    if not order:
        await callback_query.answer("Buyurtma topilmadi.", show_alert=True)
        return
    
    await state.update_data(order_id=order_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    statuses = [
        ("⏳ Kutilmoqda", "pending"),
        ("✅ To'langan", "paid"),
        ("🚚 Yetkazilmoqda", "shipped"),
        ("📦 Yetkazildi", "delivered"),
        ("❌ Bekor qilingan", "cancelled"),
    ]
    
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"admin:order:setstatus:{status}")]
        for label, status in statuses
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        f"🔄 <b>Buyurtma #{order_id} Statusini O'zgartirish</b>\n\n"
        f"Joriy status: {order.status}\n\n"
        "Yangi statusni tanlang 👇",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin:order:setstatus:"))
async def set_order_status(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Set order status."""
    new_status = callback_query.data.split(":")[-1]
    data = await state.get_data()
    order_id = data.get("order_id")
    
    try:
        order = database.execute(select(Order).where(Order.id == order_id)).scalar()
        if order:
            old_status = order.status
            order.status = new_status
            database.commit()
            
            await callback_query.message.edit_text(
                f"✅ <b>Status O'zgartirildi</b>\n\n"
                f"📋 Buyurtma #{order_id}\n"
                f"Eski status: {old_status}\n"
                f"Yangi status: {new_status}",
                parse_mode="HTML",
                reply_markup=order_actions_keyboard(),
            )
        else:
            await callback_query.answer("Buyurtma topilmadi.", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"Xato: {str(e)}", show_alert=True)
    
    await state.clear()
    await callback_query.answer()


# Broadcast handlers
@router.message(IsAdmin(), F.text == "📢 Xabar Yuborish")
async def broadcast_start(message: Message, state: FSMContext) -> None:
    """Start broadcast process."""
    await message.answer(
        "📢 <b>Xabar Yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuborilacak xabarni kiriting 👇\n\n"
        "<i>Maslahat: HTML formatlash qo'lllanadi</i>",
        reply_markup=admin_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastState.waiting_message)


@router.message(IsAdmin(), StateFilter(BroadcastState.waiting_message))
async def broadcast_message_input(message: Message, state: FSMContext) -> None:
    """Get broadcast message and send to all users."""
    broadcast_text = message.text or message.caption
    
    if not broadcast_text:
        await message.answer(
            "❌ Xabar bo'sh bo'lishi mumkin emas.",
            reply_markup=admin_cancel_keyboard(),
        )
        return
    
    # Get all users
    users = database.execute(select(User)).scalars().all()
    
    if not users:
        await message.answer(
            "❌ Foydalanuvchilar topilmadi.",
            reply_markup=admin_main_menu_keyboard(),
        )
        await state.clear()
        return
    
    sent_count = 0
    failed_count = 0
    
    await message.answer(
        f"📤 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...",
        reply_markup=None,
    )
    
    for user in users:
        try:
            if user.telegram_id:
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"📢 <b>Admin Xabari</b>\n\n{broadcast_text}",
                    parse_mode="HTML",
                )
                sent_count += 1
        except Exception as e:
            failed_count += 1
    
    await message.answer(
        f"✅ <b>Xabar Yuborish Tugallandi</b>\n\n"
        f"✅ Yuborildi: {sent_count} ta\n"
        f"❌ Muvaffaqiyatsiz: {failed_count} ta",
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="HTML",
    )
    
    await state.clear()


@router.message(IsAdmin(), F.text == "❌ Bekor qilish")
async def cancel_action(message: Message, state: FSMContext) -> None:
    """Cancel current action."""
    await state.clear()
    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=admin_main_menu_keyboard(),
    )

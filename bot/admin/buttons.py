from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


class AdminButtons:
    MAIN_MENU = "🏠 Bosh Menyusi"
    BACK = "⬅️ Orqaga"
    CANCEL = "❌ Bekor qilish"
    
    # Category management
    MANAGE_CATEGORIES = "📁 Kategoriyalar"
    ADD_CATEGORY = "➕ Kategoriya Qo'shish"
    EDIT_CATEGORY = "✏️ Kategoriya O'zgartirish"
    DELETE_CATEGORY = "🗑️ Kategoriya O'chirish"
    
    # Product management
    MANAGE_PRODUCTS = "📦 Mahsulotlar"
    ADD_PRODUCT = "➕ Mahsulot Qo'shish"
    EDIT_PRODUCT = "✏️ Mahsulot O'zgartirish"
    DELETE_PRODUCT = "🗑️ Mahsulot O'chirish"
    
    # User management
    VIEW_USERS = "👥 Foydalanuvchilar"
    
    # Order management
    MANAGE_ORDERS = "📋 Buyurtmalar"
    VIEW_ORDER_DETAILS = "👁️ Tafsilotlar"
    UPDATE_ORDER_STATUS = "🔄 Statusni O'zgartirish"
    
    # Broadcast
    BROADCAST = "📢 Xabar Yuborish"
    
    # Statistics
    STATISTICS = "📊 Statistika"


def admin_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Admin main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📁 Kategoriyalar"), KeyboardButton(text="📦 Mahsulotlar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📋 Buyurtmalar")],
            [KeyboardButton(text="📢 Xabar Yuborish"), KeyboardButton(text="📊 Statistika")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin menyusini tanlang",
    )


def admin_back_keyboard() -> ReplyKeyboardMarkup:
    """Simple back button keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Orqaga")]],
        resize_keyboard=True,
    )


def admin_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel button keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def category_actions_keyboard() -> InlineKeyboardMarkup:
    """Category management inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin:category:add"),
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="admin:category:edit"),
            ],
            [InlineKeyboardButton(text="🗑️ O'chirish", callback_data="admin:category:delete")],
            [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin:category:list")],
        ]
    )


def product_actions_keyboard() -> InlineKeyboardMarkup:
    """Product management inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin:product:add"),
                InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="admin:product:edit"),
            ],
            [InlineKeyboardButton(text="🗑️ O'chirish", callback_data="admin:product:delete")],
            [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin:product:list")],
        ]
    )


def order_actions_keyboard() -> InlineKeyboardMarkup:
    """Order management inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin:order:list")],
            [InlineKeyboardButton(text="👁️ Tafsilotlar", callback_data="admin:order:view")],
            [InlineKeyboardButton(text="🔄 Status O'zgartirish", callback_data="admin:order:status")],
        ]
    )


def order_status_keyboard() -> InlineKeyboardMarkup:
    """Order status update inline keyboard."""
    statuses = [
        ("⏳ Kutilmoqda", "pending"),
        ("✅ To'langan", "paid"),
        ("🚚 Yetkazilmoqda", "shipped"),
        ("📦 Yetkazildi", "delivered"),
        ("❌ Bekor qilingan", "cancelled"),
    ]
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"admin:order:status:{status}")]
            for label, status in statuses
        ]
    )


def list_pagination_keyboard(page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """Pagination keyboard for lists."""
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:page:{page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:page:{page + 1}"))
    
    return InlineKeyboardMarkup(inline_keyboard=[nav_buttons])

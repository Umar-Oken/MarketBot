from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.buttons import main_menu_keyboard
from bot.i18n import get_user_language

router = Router(name="help")


@router.message(Command(commands=["help"]))
async def help_command_handler(message: Message) -> None:
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    
    help_text_uz = (
        "❓ <b>Bot Haqida Yordam</b>\n\n"
        "📋 <b>Mavjud Buyruqlar:</b>\n\n"
        "🏠 /start - Asosiy menyuni ochish\n"
        "🛍️ /catalog - Mahsulotlar katalogi\n"
        "🔍 /search - Mahsulot qidirish\n"
        "🛒 /cart - Savatni ko'rish\n"
        "📦 /orders - Buyurtmalarim\n"
        "❓ /help - Bot haqida yordam\n\n"
        "💡 <b>Maslahat:</b>\n"
        "• Asosiy menyudan kerakli bo'limni tanlang\n"
        "• Mahsulotni qidirishdan foydalaning\n"
        "• Savatingizga mahsulot qo'shing va buyurtma bering"
    )
    
    help_text_ru = (
        "❓ <b>Справка по боту</b>\n\n"
        "📋 <b>Доступные команды:</b>\n\n"
        "🏠 /start - Открыть главное меню\n"
        "🛍️ /catalog - Каталог товаров\n"
        "🔍 /search - Поиск товаров\n"
        "🛒 /cart - Просмотр корзины\n"
        "📦 /orders - Мои заказы\n"
        "❓ /help - Справка по боту\n\n"
        "💡 <b>Советы:</b>\n"
        "• Выбирайте нужный раздел из главного меню\n"
        "• Используйте поиск для быстрого поиска товаров\n"
        "• Добавляйте товары в корзину и делайте заказы"
    )
    
    help_text = help_text_uz if lang == 'uz' else help_text_ru
    
    await message.answer(
        help_text,
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )

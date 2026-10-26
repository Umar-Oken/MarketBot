from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.buttons import main_menu_keyboard
from bot.i18n import get_user_language

router = Router(name="start")


async def show_main_menu(message: Message) -> None:
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    greeting_text = (
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "🎉 Online do'kon botiga xush kelibsiz!\n"
        "Quyidagi menyulardan tanlang va boshlaymiz 👇"
    ) if lang == 'uz' else (
        "👋 <b>Добро пожаловать!</b>\n\n"
        "🎉 Спасибо, что выбрали наш интернет-магазин!\n"
        "Выберите раздел и начните покупки 👇"
    )
    
    await message.answer(
        greeting_text,
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await show_main_menu(message)

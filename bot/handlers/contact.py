from aiogram import F, Router
from aiogram.types import Message

from bot.buttons import MainMenu, main_menu_keyboard
from bot.i18n import t, get_user_language

router = Router(name="contact")


@router.message(F.text.in_([t('main.contact', 'uz'), t('main.contact', 'ru')]))
async def contact_handler(message: Message) -> None:
    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'
    
    contact_text = (
        "📞 <b>" + t('main.contact', lang) + "</b>\n\n"
        "👨‍💼 <b>Admin Ma'lumotlari</b>\n"
        "├─ 📱 Telefon: <code>+998 XX XXX XX XX</code>\n"
        "├─ 💬 Telegram: <a href=\"https://t.me/your_username\"></a>\n"
        "└─ 🆔 ID: <code>7015268890</code>\n\n"
        "📍 <b>Do'kon Manzili</b>\n"
        "└─ Chorsu, Tashkent"
    ) if lang == 'uz' else (
        "📞 <b>" + t('main.contact', lang) + "</b>\n\n"
        "👨‍💼 <b>Информация Администратора</b>\n"
        "├─ 📱 Телефон: <code>+998 XX XXX XX XX</code>\n"
        "├─ 💬 Telegram: <a href=\"https://t.me/your_username\">your_username</a>\n"
        "└─ 🆔 ID: <code>7015268890</code>\n\n"
        "📍 <b>Адрес Магазина</b>\n"
        "└─ Чорсу, Ташкент"
    )
    
    await message.answer(
        contact_text,
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )

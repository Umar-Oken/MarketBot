from aiogram import F, Router
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from bot.buttons import MainMenu, main_menu_keyboard
from bot.i18n import t, get_user_language, set_user_language

router = Router(name="settings")


def settings_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Settings menu with language options and back button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t('lang.uz', lang)), KeyboardButton(text=t('lang.ru', lang))],
            [KeyboardButton(text=t('common.back', lang))],
        ],
        resize_keyboard=True,
    )


@router.message(F.text.in_([t('main.settings', 'uz'), t('main.settings', 'ru')]))
async def settings_handler(message: Message) -> None:
    lang = get_user_language(message.from_user.id) if (message.from_user and hasattr(message.from_user, 'id')) else 'uz'
    # show language options
    await message.answer(
        t('settings.title', lang) + t('settings.description', lang),
        reply_markup=settings_keyboard(lang),
        parse_mode="HTML",
    )


@router.message(F.text.in_([t('lang.uz', 'uz'), t('lang.ru', 'uz'), t('lang.uz', 'ru'), t('lang.ru', 'ru')]))
async def language_selection_handler(message: Message) -> None:
    # map text to language code
    text = message.text
    if text in (t('lang.uz', 'uz'), t('lang.uz', 'ru')):
        lang_code = 'uz'
        lang_name = t('lang.uz', 'uz')
    else:
        lang_code = 'ru'
        lang_name = t('lang.ru', 'ru')

    if message.from_user and hasattr(message.from_user, 'id'):
        set_user_language(message.from_user.id, lang_code)

    await message.answer(
        t('settings.lang_set', lang_code).format(lang_name=lang_name),
        reply_markup=main_menu_keyboard(lang_code),
    )


@router.message(F.text.in_([t('common.back', 'uz'), t('common.back', 'ru')]))
async def back_to_menu_handler(message: Message) -> None:
    """Back button from settings to main menu."""
    lang = get_user_language(message.from_user.id) if (message.from_user and hasattr(message.from_user, 'id')) else 'uz'
    await message.answer(
        "🏠 " + t('main.placeholder', lang),
        reply_markup=main_menu_keyboard(lang),
    )

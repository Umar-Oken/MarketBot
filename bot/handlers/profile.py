from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select

from bot.buttons import MainMenu, main_menu_keyboard
from bot.i18n import t, get_user_language
from db import database
from db.models import User

router = Router(name="profile")


@router.message(F.text.in_([t('main.profile', 'uz'), t('main.profile', 'ru')]))
async def profile_handler(message: Message) -> None:
    if message.from_user is None:
        await message.answer(
            t('profile.not_found', 'uz'),
            reply_markup=main_menu_keyboard('uz'),
        )
        return

    user = database.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    ).scalars().first()

    lang = get_user_language(message.from_user.id) if message.from_user else 'uz'

    if user is None:
        await message.answer(
            t('profile.header', lang) + "\n" + t('profile.not_registered', lang),
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        return

    username = f"@{message.from_user.username}" if message.from_user.username else t('common.not_available', lang)
    if user.created_at:
        registration_date = user.created_at.strftime("%d.%m.%Y")
    else:
        registration_date = t('common.not_available', lang)
    orders_count = len(user.orders) if user.orders else 0

    profile_text = (
        t('profile.header', lang) + "\n"
        + f"{t('profile.field_name', lang)}: <code>{user.first_name} {user.last_name}</code>\n"
        + f"{t('profile.field_phone', lang)}: <code>{user.phone}</code>\n"
        + f"{t('profile.field_username', lang)}: {username}\n"
        + f"{t('profile.field_registration', lang)}: {registration_date}\n"
        + f"{t('profile.field_orders', lang)}: {orders_count}"
    )

    await message.answer(
        profile_text,
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )


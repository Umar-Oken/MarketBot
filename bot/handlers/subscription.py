from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="subscription")


@router.callback_query(F.data == "check_if_subscribed")
async def handle_check_if_subscribed(callback_query: CallbackQuery) -> None:
    await callback_query.answer("✅ Tekshirish bosildi")

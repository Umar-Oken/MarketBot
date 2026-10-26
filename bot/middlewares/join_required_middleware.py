from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder



class JoinChannelGroupMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.CHAT_IDES = [-1003779710392, -1003931875778]

    async def __call__(self, handler, event: Update, data) -> Any:
        bot: Bot = data["bot"]
        if event.callback_query or event.message:
            if event.callback_query:
                user = event.callback_query.from_user
            else:
                user = event.message.from_user
            unsubscribes = []
            for channel in self.CHAT_IDES:
                try:
                    member = await bot.get_chat_member(channel, user.id)
                    if member.status == ChatMemberStatus.LEFT:
                        unsubscribes.append(channel)
                except TelegramBadRequest:
                    pass
            if unsubscribes:
                ikb = InlineKeyboardBuilder()
                for channel_id in unsubscribes:
                    channel = (await bot.get_chat(channel_id)).model_dump()
                    ikb.add(InlineKeyboardButton(text=channel["title"], url=channel["invite_link"]))
                ikb.add(InlineKeyboardButton(text="A'zo bo'ldim✅", callback_data="check_if_subscribed"))
                ikb.adjust(1, repeat=True)
                if event.callback_query:
                    callback_answered = False
                    if event.callback_query.message is not None:
                        try:
                            await event.callback_query.message.edit_text(
                                "Oldin kanallarga a'zo bo'ling!",
                                reply_markup=ikb.as_markup(),
                            )
                        except TelegramBadRequest:
                            await event.callback_query.answer("Hali hammasiga a'zo bo'lmadingiz!")
                            callback_answered = True
                    else:
                        await bot.send_message(
                            event.callback_query.from_user.id,
                            "Oldin kanallarga a'zo bo'ling!",
                            reply_markup=ikb.as_markup(),
                        )
                    if not callback_answered:
                        await event.callback_query.answer(
                            "Oldin kanallarga a'zo bo'ling!",
                            show_alert=True,
                        )
                    return
                else:
                    await event.message.answer("Oldin kanallarga a'zo bo'ling!", reply_markup=ikb.as_markup())
                    return
        return await handler(event, data)

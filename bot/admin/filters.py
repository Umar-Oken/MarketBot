from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import settings


class IsAdmin(BaseFilter):
    """Filter to check if user is admin."""
    
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        user_id = None
        
        if isinstance(message, Message):
            user_id = message.from_user.id if message.from_user else None
        elif isinstance(message, CallbackQuery):
            user_id = message.from_user.id if message.from_user else None
        
        if user_id is None:
            return False
        
        return user_id in settings.admin_ids

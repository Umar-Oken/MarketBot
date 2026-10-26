from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from bot.i18n import t


class MainMenu:
    # keep defaults for backwards compatibility (Uzbek default)
    CATALOG = "🛍️ Katalog"
    CART = "🛒 Savat"
    ORDERS = "📦 Buyurtmalarim"
    SEARCH = "🔍 Qidirish"
    PROFILE = "👤 Profil"
    CONTACT = "📞 Aloqa"
    SETTINGS = "⚙️ Sozlamalar"


def main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Modern main menu with improved layout and clear grouping."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t('main.catalog', lang)),
                KeyboardButton(text=t('main.search', lang)),
            ],
            [
                KeyboardButton(text=t('main.cart', lang)),
                KeyboardButton(text=t('main.orders', lang)),
            ],
            [
                KeyboardButton(text=t('main.profile', lang)),
                KeyboardButton(text=t('main.contact', lang)),
            ],
            [
                KeyboardButton(text=t('main.settings', lang)),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=t('main.placeholder', lang),
    )

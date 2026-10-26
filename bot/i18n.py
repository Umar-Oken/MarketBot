import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "user_languages.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

TRANSLATIONS = {
    "uz": {
        "main": {
            "catalog": "🛍️ Katalog",
            "cart": "🛒 Savat",
            "orders": "📦 Buyurtmalarim",
            "search": "🔍 Qidirish",
            "profile": "👤 Profil",
            "contact": "📞 Aloqa",
            "settings": "⚙️ Sozlamalar",
            "placeholder": "👇 Kerakli bo'limni tanlang",
        },
        "settings": {
            "title": "⚙️ <b>Sozlamalar</b>\n",
            "description": "<b>Tilni tanlang:</b>",
            "lang_set": "✅ Til o'zgartirildi: <b>{lang_name}</b>",
            "back": "⬅️ Orqaga",
        },
        "lang": {
            "uz": "🇺🇿 Ўзбекча",
            "ru": "🇷🇺 Русский",
        },
        "profile": {
            "not_found": "❌ Foydalanuvchi aniqlanmadi.",
            "header": "👤 <b>Profil</b>\n",
            "not_registered": "ℹ️ Siz hali ro'yxatdan o'tmadingiz.\nBirinchi buyurtma berish uchun ro'yxatdan o'ting.",
            "field_name": "📛 Ism Sharifi",
            "field_phone": "📞 Telefon Raqam",
            "field_registration": "📅 Ro'yxatdan O'tgan Sana",
            "field_username": "💬 Telegram Username",
            "field_orders": "📦 Buyurtmalar Soni",
        },
        "orders": {
            "empty": "📭 Sizning buyurtmalaringiz hali yo'q.",
        },
        "common": {
            "not_available": "–",
            "back": "⬅️ Orqaga",
        },
    },
    "ru": {
        "main": {
            "catalog": "🛍️ Каталог",
            "cart": "🛒 Корзина",
            "orders": "📦 Мои заказы",
            "search": "🔍 Поиск",
            "profile": "👤 Профиль",
            "contact": "📞 Контакты",
            "settings": "⚙️ Настройки",
            "placeholder": "👇 Выберите раздел",
        },
        "settings": {
            "title": "⚙️ <b>Настройки</b>\n",
            "description": "<b>Выберите язык:</b>",
            "lang_set": "✅ Язык изменён: <b>{lang_name}</b>",
            "back": "⬅️ Назад",
        },
        "lang": {
            "uz": "🇺🇿 Узбекский",
            "ru": "🇷🇺 Русский",
        },
        "profile": {
            "not_found": "❌ Пользователь не найден.",
            "header": "👤 <b>Профиль</b>\n",
            "not_registered": "ℹ️ Вы ещё не зарегистрированы.\nПожалуйста, зарегистрируйтесь для оформления заказа.",
            "field_name": "📛 ФИО",
            "field_phone": "📞 Телефон",
            "field_registration": "📅 Дата регистрации",
            "field_username": "💬 Telegram Username",
            "field_orders": "📦 Количество заказов",
        },
        "orders": {
            "empty": "📭 У вас ещё нет заказов.",
        },
        "common": {
            "not_available": "–",
            "back": "⬅️ Назад",
        },
    },
}


def _load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def t(key: str, lang: str = "uz") -> str:
    """
    Translate a key using dot notation (e.g., 'main.catalog').
    If translation is not found, logs error and returns the key.
    """
    parts = key.split(".")
    node = TRANSLATIONS.get(lang, TRANSLATIONS["uz"])
    
    for i, part in enumerate(parts):
        if isinstance(node, dict):
            node = node.get(part)
        else:
            # Path was invalid, log and return key
            logger.error(f"Translation key '{key}' not found for language '{lang}'")
            return key
        
        if node is None:
            # Key part not found, log and return the original key
            logger.error(f"Translation key '{key}' not found for language '{lang}'")
            return key
    
    return node if isinstance(node, str) else key


def get_user_language(telegram_id: int) -> str:
    data = _load_data()
    return data.get(str(telegram_id), "uz")


def set_user_language(telegram_id: int, lang: str) -> None:
    data = _load_data()
    data[str(telegram_id)] = lang
    _save_data(data)

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def _parse_admin_ids(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()

    admin_ids = []
    normalized_value = value.replace(";", ",").replace(" ", ",")
    for raw_item in normalized_value.split(","):
        item = raw_item.strip()
        if item.startswith("-"):
            is_integer = item[1:].isdigit()
        else:
            is_integer = item.isdigit()
        if is_integer:
            admin_ids.append(int(item))
    return tuple(admin_ids)


class Settings:
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    SECRET_KEY = os.getenv("SECRET_KEY")

    def __init__(self, database, user, password, host, port, admin_ids):
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = int(port) if port else None
        self.admin_ids = _parse_admin_ids(admin_ids)
        self.public_base_url = (os.getenv("PUBLIC_BASE_URL") or os.getenv("WEB_BASE_URL") or "").rstrip("/")
        self.database_url = os.getenv("DATABASE_URL")

    def postgresql_url(self) -> URL:
        if self.database_url:
            return make_url(self.database_url)
        return URL.create(
            "postgresql",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def alembic_url(self) -> str:
        return self.postgresql_url().render_as_string(hide_password=False).replace("%", "%%")


settings = Settings(
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    admin_ids=os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID") or os.getenv("ADMINS"),

)

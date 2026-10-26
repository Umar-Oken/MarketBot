import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from starlette_admin import I18nConfig
from starlette_admin.contrib.sqla import Admin
from starlette_admin.contrib.sqla import ModelView

from config import settings
from db import User, Category, Product, Order, Payment
from db.base import db
from db.storage import MEDIA_DIR, PROJECT_ROOT, configure_file_storage
from web.provider import UsernameAndPasswordProvider

configure_file_storage()

middleware = [
    Middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, https_only=True)
]

app = Starlette(middleware=middleware)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/images", StaticFiles(directory=PROJECT_ROOT / "images"), name="images")

i18n_config = I18nConfig(
    default_locale="uz"
)
logo_url = 'https://i.ibb.co/NgjxKy0c/china-uzbek.jpg'
admin = Admin(
    engine=db._engine,
    title="Online Shop",
    templates_dir='templates/admin/index.html',
    base_url='/',
    logo_url=logo_url,
    login_logo_url='https://i.ibb.co/RkbDfwS7/login-logo-2.jpg',
    auth_provider=UsernameAndPasswordProvider(),
    i18n_config=i18n_config
)


class UserModelView(ModelView):
    label = "🤵 Klientlar"
    # list_template = ''

    fields_default_sort = 'last_name', 'first_name', 'phone'
    searchable_fields = 'last_name', 'first_name', 'phone'
    exclude_fields_from_edit = 'created_at', 'updated_at'


class CategoryModelView(ModelView):
    label = "🍡Kategoriyalar"
    exclude_fields_from_create = 'created_at', 'updated_at'
    exclude_fields_from_edit = 'created_at', 'updated_at'


class ProductModelView(ModelView):
    label = "🧈Maxsulotlar"
    fields = (
        "id",
        "category",
        "name",
        "photo",
        "description",
        "price",
        "stock_quantity",
        "is_active",
    )
    exclude_fields_from_create = 'id',
    exclude_fields_from_edit = 'id',


class OrderModelView(ModelView):
    label = "Buyurtmalar"
    fields = "id", "status", "user", "total_amount"
    exclude_fields_from_create = 'created_at',
    exclude_fields_from_edit = 'created_at',


class PaymentModelView(ModelView):
    label = "💲To'lovlar"
    exclude_fields_from_create = 'created_at', 'updated_at'
    exclude_fields_from_edit = 'created_at', 'updated_at'


admin.add_view(UserModelView(User))
admin.add_view(CategoryModelView(Category))
admin.add_view(ProductModelView(Product))
admin.add_view(OrderModelView(Order))
admin.add_view(PaymentModelView(Payment))

# Mount admin to your app
admin.mount_to(app)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8088)

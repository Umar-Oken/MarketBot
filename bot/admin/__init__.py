from bot.admin import main, categories, products, orders_broadcast

admin_routers = (
    main.router,
    categories.router,
    products.router,
    orders_broadcast.router,
)

__all__ = ("admin_routers",)

from bot.handlers import cart, catalog, contact, help, orders, profile, settings, start, subscription
from bot.admin import admin_routers

routers = (
    start.router,
    help.router,
    subscription.router,
    catalog.router,
    cart.router,
    orders.router,
    profile.router,
    contact.router,
    settings.router,
) + admin_routers

__all__ = ("routers",)

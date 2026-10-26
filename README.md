# MarketBot

## Environment setup

1. Copy `.env.example` to `.env`.
2. Replace the example values with your Telegram bot token, PostgreSQL credentials, Telegram admin IDs, and admin panel credentials.
3. Set `SECRET_KEY` to a long, randomly generated value before exposing the admin panel.
4. Start the bot using your usual Python environment and database setup.

You can provide the database connection either as `DATABASE_URL` or as the
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` values. Keep `.env`
private; it is excluded from Git. `.env.example` contains placeholders only.

The admin app binds to localhost when run directly and only accepts its session
cookie over HTTPS. To expose it remotely, put it behind a correctly configured
HTTPS reverse proxy.

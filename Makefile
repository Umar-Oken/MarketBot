extract:
	pybabel extract --input-dirs=. -o locales/messages.pot # SEARCH FROM ALL FILES I18N

init:
	pybabel init -i locales/messages.pot -d locales -D messages -l ru
	pybabel init -i locales/messages.pot -d locales -D messages -l uz

compile:
	pybabel compile -d locales -D messages # po file to mo file (The type that only computer understands)!

update:
	pybabel update -d locales -D messages -i locales/messages.pot


revision:
	alembic revision --autogenerate -m "Create users table"
upgrade:
	alembic upgrade head
downgrade:
	alembic downgrade -1
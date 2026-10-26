"""Use bigint for Telegram IDs

Revision ID: 7f2974b1b258
Revises: 48cfd011f54b
Create Date: 2026-07-17 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f2974b1b258'
down_revision: Union[str, Sequence[str], None] = '48cfd011f54b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'users',
        'telegram_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        'baskets',
        'telegram_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'baskets',
        'telegram_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        'users',
        'telegram_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )

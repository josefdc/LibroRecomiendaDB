"""Refine models relationships constraints indexes

Revision ID: 4a1402d984cd
Revises: 3066cc73b616
Create Date: 2025-04-27 19:04:55.759191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a1402d984cd'
down_revision: Union[str, None] = '3066cc73b616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('uq_user_book_review', 'reviews', ['user_id', 'book_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('uq_user_book_review', 'reviews', type_='unique')
    # ### end Alembic commands ###

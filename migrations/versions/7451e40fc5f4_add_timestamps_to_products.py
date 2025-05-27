"""add_timestamps_to_products

Revision ID: 7451e40fc5f4
Revises: f7eef339bf90
Create Date: 2025-05-27 12:39:04.373561

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7451e40fc5f4'
down_revision = 'f7eef339bf90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('products', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'created_at')
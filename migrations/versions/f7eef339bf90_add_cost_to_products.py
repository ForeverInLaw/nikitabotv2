"""add_cost_to_products

Revision ID: f7eef339bf90
Revises: 9da0620cd6fc
Create Date: 2025-05-27 12:35:57.562322

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7eef339bf90'
down_revision = '9da0620cd6fc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('cost', sa.Numeric(10, 2), nullable=False))


def downgrade() -> None:
    op.drop_column('products', 'cost')

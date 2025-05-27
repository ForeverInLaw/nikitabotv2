"""add_variation_to_products

Revision ID: 9da0620cd6fc
Revises: a1b2c3d4e5f6
Create Date: 2025-05-27 12:25:38.495649

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9da0620cd6fc'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('variation', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('products', 'variation')

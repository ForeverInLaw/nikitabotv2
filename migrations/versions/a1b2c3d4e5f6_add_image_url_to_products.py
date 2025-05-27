"""Add image_url to products

Revision ID: a1b2c3d4e5f6
Revises: 6cb8ed9715a5
Create Date: 2023-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6cb8ed9715a5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('image_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('products', 'image_url')

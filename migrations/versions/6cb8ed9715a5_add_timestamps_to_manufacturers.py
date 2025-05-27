"""add_timestamps_to_manufacturers

Revision ID: 6cb8ed9715a5
Revises: 
Create Date: 2025-05-27 09:15:21.550960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6cb8ed9715a5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('manufacturers', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('manufacturers', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False))


def downgrade() -> None:
    op.drop_column('manufacturers', 'updated_at')
    op.drop_column('manufacturers', 'created_at')







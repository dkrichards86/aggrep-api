"""empty message

Revision ID: 75fa42054d36
Revises: 3ea5ffecc489
Create Date: 2019-11-22 11:42:42.741094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75fa42054d36'
down_revision = '3ea5ffecc489'
branch_labels = None
depends_on = None

upgrade_type = sa.Numeric(4, 3)
downgrade_type = sa.Integer()


def upgrade():
    op.alter_column('post_actions', 'ctr', type_=upgrade_type, existing_type=downgrade_type)


def downgrade():
    op.alter_column('post_actions', 'ctr', type_=downgrade_type, existing_type=upgrade_type)

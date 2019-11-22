"""empty message

Revision ID: dc28ec9c7885
Revises: 016d13a4d3fc
Create Date: 2019-11-22 11:16:27.222493

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc28ec9c7885'
down_revision = '016d13a4d3fc'
branch_labels = None
depends_on = None


def upgrade():
    from aggrep.models import PostAction
    for pa in PostAction.query.all():
        pa.update(ctr=0)


def downgrade():
    pass

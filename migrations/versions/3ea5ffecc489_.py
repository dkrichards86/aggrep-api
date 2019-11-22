"""empty message

Revision ID: 3ea5ffecc489
Revises: dc28ec9c7885
Create Date: 2019-11-22 11:24:27.360119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ea5ffecc489'
down_revision = 'dc28ec9c7885'
branch_labels = None
depends_on = None


upgrade_type = sa.Enum('COLLECT', 'PROCESS', 'RELATE', 'ANALYZE', name='jobs')
downgrade_type = sa.Enum('COLLECT', 'PROCESS', 'RELATE', name='jobs')


def upgrade():
    op.alter_column('joblock', 'job', type_=upgrade_type, existing_type=downgrade_type)


def downgrade():
    op.alter_column('joblock', 'job', type_=downgrade_type, existing_type=upgrade_type)


"""empty message

Revision ID: 4c93f6f42704
Revises: 3eba9f786ead
Create Date: 2019-11-22 12:36:18.579092

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c93f6f42704'
down_revision = '3eba9f786ead'
branch_labels = None
depends_on = None


def upgrade():
    job_types = ('COLLECT', 'PROCESS', 'RELATE', 'ANALYZE')
    
    from aggrep import db
    from aggrep.models import JobType
    for jt in job_types:
        JobType.create(job=jt)


def downgrade():
    pass

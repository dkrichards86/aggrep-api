"""empty message

Revision ID: 029946997791
Revises: 6f5bfc08b917
Create Date: 2020-01-26 13:17:27.977027

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy_searchable import sql_expressions

Session = sessionmaker()

# revision identifiers, used by Alembic.
revision = '029946997791'
down_revision = '6f5bfc08b917'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    session.execute(sql_expressions)


def downgrade():
    pass

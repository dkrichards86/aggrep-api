"""empty message

Revision ID: 714930acb147
Revises: c206598699f4
Create Date: 2019-11-21 19:58:08.735378

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '714930acb147'
down_revision = 'c206598699f4'
branch_labels = None
depends_on = None


def upgrade():
    from aggrep import db
    from aggrep.models import Post, PostAction
    for p in Post.query.all():
        PostAction.create(post_id=p.id)

    db.session.commit()


def downgrade():
    pass

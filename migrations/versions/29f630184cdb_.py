"""empty message

Revision ID: 29f630184cdb
Revises: 029946997791
Create Date: 2020-01-26 13:56:07.388070

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()


# revision identifiers, used by Alembic.
revision = '29f630184cdb'
down_revision = '029946997791'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('entities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity', sa.String(length=40), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entities_post_id'), 'entities', ['post_id'], unique=False)
    op.create_table('entity_queue',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id')
    )

    bind = op.get_bind()
    session = Session(bind=bind)
    session.execute("INSERT INTO job_types(job) VALUES ('PROCESS');")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('entity_queue')
    op.drop_index(op.f('ix_entities_post_id'), table_name='entities')
    op.drop_table('entities')

    bind = op.get_bind()
    session = Session(bind=bind)
    session.execute("DELETE FROM job_types WHERE job = 'PROCESS';")
    # ### end Alembic commands ###

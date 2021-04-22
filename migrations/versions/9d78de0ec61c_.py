"""empty message

Revision ID: 9d78de0ec61c
Revises: 9199ebeb0baf
Create Date: 2021-04-22 13:48:28.668157

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9d78de0ec61c'
down_revision = '9199ebeb0baf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('following_ibfk_2', 'following', type_='foreignkey')
    op.drop_column('following', 'tag_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('following', sa.Column('tag_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.create_foreign_key('following_ibfk_2', 'following', 'tag', ['tag_id'], ['id'])
    # ### end Alembic commands ###
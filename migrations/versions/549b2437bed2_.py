"""empty message

Revision ID: 549b2437bed2
Revises: 6fa5d6e0ea3f
Create Date: 2021-04-22 14:56:25.672232

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '549b2437bed2'
down_revision = '6fa5d6e0ea3f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('following', sa.Column('download', sa.Boolean(), nullable=True))
    op.drop_column('following', 'feedback')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('following', sa.Column('feedback', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    op.drop_column('following', 'download')
    # ### end Alembic commands ###
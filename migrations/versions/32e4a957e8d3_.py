"""empty message

Revision ID: 32e4a957e8d3
Revises: b7241515231f
Create Date: 2021-04-02 19:06:30.865740

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '32e4a957e8d3'
down_revision = 'b7241515231f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('following', 'status')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('following', sa.Column('status', mysql.VARCHAR(length=255), nullable=True))
    # ### end Alembic commands ###
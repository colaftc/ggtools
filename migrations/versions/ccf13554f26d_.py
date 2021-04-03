"""empty message

Revision ID: ccf13554f26d
Revises: 26110289b7a1
Create Date: 2021-04-03 10:30:26.888549

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ccf13554f26d'
down_revision = '26110289b7a1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('following', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'))
    op.alter_column('following', 'created_at',
               existing_type=mysql.DATETIME(),
               comment='创建时间',
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('following', 'created_at',
               existing_type=mysql.DATETIME(),
               comment=None,
               existing_comment='创建时间',
               existing_nullable=True)
    op.drop_column('following', 'updated_at')
    # ### end Alembic commands ###

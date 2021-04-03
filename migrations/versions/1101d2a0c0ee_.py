"""empty message

Revision ID: 1101d2a0c0ee
Revises: 
Create Date: 2021-04-03 11:14:20.710641

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from models import FollowStatusChoices


# revision identifiers, used by Alembic.
revision = '1101d2a0c0ee'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('following',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('company', sa.String(length=100), nullable=True),
    sa.Column('tel', sa.String(length=20), nullable=True),
    sa.Column('status', sqlalchemy_utils.types.choice.ChoiceType(FollowStatusChoices), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('seller',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('tel', sa.String(length=50), nullable=True),
    sa.Column('status', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('tel')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('seller')
    op.drop_table('following')
    # ### end Alembic commands ###

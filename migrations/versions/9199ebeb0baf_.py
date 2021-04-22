"""empty message

Revision ID: 9199ebeb0baf
Revises: ac8a919947e5
Create Date: 2021-04-22 12:38:13.006748

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9199ebeb0baf'
down_revision = 'ac8a919947e5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('client_info',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('company', sa.String(length=255), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('tel', sa.String(length=50), nullable=True),
    sa.Column('industry', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tel')
    )
    op.create_table('tag',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tags_map',
    sa.Column('tag_id', sa.Integer(), nullable=True),
    sa.Column('following_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['following_id'], ['following.id'], ),
    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], )
    )
    op.add_column('following', sa.Column('markup', sa.String(length=200), nullable=True))
    op.add_column('following', sa.Column('tag_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'following', 'tag', ['tag_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'following', type_='foreignkey')
    op.drop_column('following', 'tag_id')
    op.drop_column('following', 'markup')
    op.drop_table('tags_map')
    op.drop_table('tag')
    op.drop_table('client_info')
    # ### end Alembic commands ###
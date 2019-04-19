"""Use multi-table inheritance on requests

Revision ID: 60462ac53829
Revises: 91034691bf96
Create Date: 2019-04-19 02:54:39.225898

"""
from alembic import op
from geoalchemy2.types import Geometry
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = '60462ac53829'
down_revision = '91034691bf96'
branch_labels = None
depends_on = None


business_entity_status = postgresql.ENUM(
    'kids_exclusive', 'kids_exclusive_withdrawn',
    'kids_friendly', 'out_of_business', 'paused',
    'duplicate', name='business_entity_status', create_type=False
)
revision_kind = sa.Enum(
    'name', 'category', 'status', 'location', name='revision_kind'
)


def upgrade():
    op.create_table(
        'block_user_request',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('blocking_user_id', UUIDType, nullable=False),
        sa.ForeignKeyConstraint(['blocking_user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['id'], ['request.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'creation_request',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('name', sa.Unicode(), nullable=False),
        sa.Column('category', sa.Unicode(), nullable=False),
        sa.Column('status', business_entity_status, nullable=False),
        sa.Column('address', sa.Unicode(), nullable=False),
        sa.Column('address_sub', sa.Unicode(), nullable=False),
        sa.Column('coordinate', Geometry(geometry_type='POINT'), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['request.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'mark_as_duplicate_request',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('business_entity_id', UUIDType, nullable=False),
        sa.Column('duplicates_with_id', UUIDType, nullable=False),
        sa.ForeignKeyConstraint(['business_entity_id'], ['business_entity.id'], ),
        sa.ForeignKeyConstraint(['duplicates_with_id'], ['business_entity.id'], ),
        sa.ForeignKeyConstraint(['id'], ['request.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'revision_request',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('business_entity_id', UUIDType, nullable=False),
        sa.Column('revision_kind', revision_kind, nullable=False),
        sa.Column('data', postgresql.JSON, nullable=False),
        sa.ForeignKeyConstraint(['business_entity_id'], ['business_entity.id'], ),
        sa.ForeignKeyConstraint(['id'], ['request.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.drop_constraint('request_duplicates_with_id_fkey', 'request', type_='foreignkey')
    op.drop_constraint('request_business_entity_id_fkey', 'request', type_='foreignkey')
    op.drop_constraint('request_blocking_user_id_fkey', 'request', type_='foreignkey')
    op.drop_column('request', 'business_entity_id')
    op.drop_column('request', 'data')
    op.drop_column('request', 'blocking_user_id')
    op.drop_column('request', 'duplicates_with_id')


def downgrade():
    revision_kind.drop(op.get_bind())
    op.add_column('request', sa.Column('duplicates_with_id', postgresql.UUID(), autoincrement=False, nullable=True))
    op.add_column('request', sa.Column('blocking_user_id', postgresql.UUID(), autoincrement=False, nullable=True))
    op.add_column('request', sa.Column('data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('request', sa.Column('business_entity_id', postgresql.UUID(), autoincrement=False, nullable=True))
    op.create_foreign_key('request_blocking_user_id_fkey', 'request', 'user', ['blocking_user_id'], ['id'])
    op.create_foreign_key('request_business_entity_id_fkey', 'request', 'business_entity', ['business_entity_id'], ['id'])
    op.create_foreign_key('request_duplicates_with_id_fkey', 'request', 'business_entity', ['duplicates_with_id'], ['id'])
    op.drop_table('revision_request')
    op.drop_table('mark_as_duplicate_request')
    op.drop_table('creation_request')
    op.drop_table('block_user_request')

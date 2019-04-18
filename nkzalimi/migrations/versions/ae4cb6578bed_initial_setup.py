"""Initial setup

Revision ID: ae4cb6578bed
Revises: 
Create Date: 2019-04-17 18:11:36.733023

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy_utc import UtcDateTime
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = 'ae4cb6578bed'
down_revision = None
branch_labels = None
depends_on = None


oauth_provider_type = sa.Enum(
    'facebook', 'instagram', 'twitter', 'github', name='oauth_provider'
)
business_entity_status = sa.Enum(
    'pending', 'kids_exclusive', 'kids_exclusive_withdrawn',
    'kids_friendly', 'out_of_business', 'paused',
    'duplicate', name='business_entity_status'
)
request_kind = sa.Enum(
    'creation', 'mark_as_duplicate', 'revision', 'block_user',
    name='request_kind'
)


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('display_name', sa.Unicode(), nullable=False),
        sa.Column('admin', sa.Boolean(), nullable=False),
        sa.Column('created_at', UtcDateTime, nullable=False),
        sa.Column('blocked_at', UtcDateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_user_created_at'),
        'user', ['created_at'], unique=False
    )
    op.create_table(
        'attachment',
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('mimetype', sa.String(length=255), nullable=False),
        sa.Column('original', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', UUIDType, nullable=False),
        sa.PrimaryKeyConstraint('width', 'height', 'id')
    )
    op.create_table(
        'business_entity',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('latest_revision_id', UUIDType, nullable=True),
        sa.Column('first_revision_id', UUIDType, nullable=True),
        sa.Column('created_at', UtcDateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_business_entity_latest_revision_id'), 'business_entity',
        ['latest_revision_id'], unique=True
    )
    op.create_index(
        op.f('ix_business_entity_created_at'), 'business_entity',
        ['created_at'], unique=False
    )
    op.create_table(
        'business_entity_revision',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('replacing_id', UUIDType, nullable=True),
        sa.Column('created_at', UtcDateTime, nullable=False),
        sa.Column('request_id', UUIDType, nullable=False),
        sa.Column('name', sa.Unicode(), nullable=False),
        sa.Column('category', sa.Unicode(), nullable=False),
        sa.Column('status', business_entity_status, nullable=False),
        sa.Column('address', sa.Unicode(), nullable=False),
        sa.Column('address_sub', sa.Unicode(), nullable=False),
        sa.Column('lat', sa.Numeric(precision=15), nullable=False),
        sa.Column('lng', sa.Numeric(precision=15), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_foreign_key(
        'fk_business_entity_replacing_id_first_revision_id',
        'business_entity', 'business_entity_revision',
        ['first_revision_id'], ['id']
    )
    op.create_foreign_key(
        'fk_business_entity_replacing_id_latest_revision_id',
        'business_entity', 'business_entity_revision',
        ['latest_revision_id'], ['id']
    )
    op.create_foreign_key(
        'fk_business_entity_revision_replacing_id',
        'business_entity_revision', 'business_entity_revision',
        ['replacing_id'], ['id']
    )
    op.create_index(
        op.f('ix_business_entity_revision_request_id'),
        'business_entity_revision', ['request_id'], unique=True
    )
    op.create_index(
        op.f('ix_business_entity_revision_category'),
        'business_entity_revision', ['category'], unique=False
    )
    op.create_index(
        op.f('ix_business_entity_revision_created_at'),
        'business_entity_revision', ['created_at'], unique=False
    )
    op.create_index(
        op.f('ix_business_entity_revision_lat'),
        'business_entity_revision', ['lat'], unique=False
    )
    op.create_index(
        op.f('ix_business_entity_revision_lng'),
        'business_entity_revision', ['lng'], unique=False)
    op.create_table(
        'request',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('created_at', UtcDateTime, nullable=False),
        sa.Column('submitted_by_id', UUIDType, nullable=False),
        sa.Column('kind', request_kind, nullable=False),
        sa.Column('data', JSON, nullable=True),
        sa.Column('business_entity_id', UUIDType, nullable=True),
        sa.Column('duplicates_with_id', UUIDType, nullable=True),
        sa.Column('blocking_user_id', UUIDType, nullable=True),
        sa.ForeignKeyConstraint(['business_entity_id'], ['business_entity.id'], ),
        sa.ForeignKeyConstraint(['blocking_user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['duplicates_with_id'], ['business_entity.id'], ),
        sa.ForeignKeyConstraint(['submitted_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_request_created_at'),
        'request', ['created_at'], unique=False
    )
    op.create_index(
        op.f('ix_request_kind'),
        'request', ['kind'], unique=False
    )
    op.create_foreign_key(
        'fk_attachment_id', 'attachment', 'request', ['id'], ['id']
    )
    op.create_foreign_key(
        'fk_business_entity_request_id',
        'business_entity_revision', 'request',
        ['request_id'], ['id']
    )
    op.create_table(
        'poll',
        sa.Column('user_id', UUIDType, nullable=False),
        sa.Column('request_id', UUIDType, nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['request.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'request_id')
    )
    op.create_index(
        op.f('ix_poll_request_id'),
        'poll', ['request_id'], unique=False
    )
    op.create_table(
        'oauth_login',
        sa.Column('id', UUIDType, nullable=False),
        sa.Column('user_id', UUIDType, nullable=False),
        sa.Column('provider', oauth_provider_type, nullable=False),
        sa.Column('uid', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'uid', name='uc_oauth_login_provider_uid')
    )
    op.create_index(
        op.f('ix_oauth_login_user_id'),
        'oauth_login', ['user_id'], unique=False
    )


def downgrade():
    bind = op.get_bind()
    op.drop_index(op.f('ix_oauth_login_user_id'), table_name='oauth_login')
    op.drop_table('oauth_login')
    op.drop_index(op.f('ix_poll_request_id'), table_name='poll')
    op.drop_table('poll')
    op.drop_constraint('fk_business_entity_replacing_id_latest_revision_id',
                       'business_entity', type_='foreignkey')
    op.drop_constraint('fk_business_entity_replacing_id_first_revision_id',
                       'business_entity', type_='foreignkey')
    op.drop_index(op.f('ix_business_entity_revision_lng'), table_name='business_entity_revision')
    op.drop_index(op.f('ix_business_entity_revision_lat'), table_name='business_entity_revision')
    op.drop_index(op.f('ix_business_entity_revision_created_at'), table_name='business_entity_revision')
    op.drop_index(op.f('ix_business_entity_revision_category'), table_name='business_entity_revision')
    op.drop_table('business_entity_revision')
    op.drop_index(op.f('ix_request_kind'), table_name='request')
    op.drop_index(op.f('ix_request_created_at'), table_name='request')
    op.drop_table('request')
    op.drop_index(op.f('ix_business_entity_created_at'), table_name='business_entity')
    op.drop_table('business_entity')
    op.drop_table('attachment')
    op.drop_index(op.f('ix_user_created_at'), table_name='user')
    op.drop_table('user')
    oauth_provider_type.drop(bind, checkfirst=False)
    business_entity_status.drop(bind, checkfirst=False)
    request_kind.drop(bind, checkfirst=False)

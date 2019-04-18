"""Use PostGIS geometry

Revision ID: 91034691bf96
Revises: c450e75de4c8
Create Date: 2019-04-18 23:17:01.834513

"""
from alembic import op
from geoalchemy2.types import Geometry
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91034691bf96'
down_revision = 'c450e75de4c8'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute('CREATE EXTENSION postgis')
    op.add_column(
        'business_entity_revision',
        sa.Column('coordinate', Geometry(geometry_type='POINT'), nullable=False)
    )
    op.create_index('ix_business_entity_revision_coordinate',
                    'business_entity_revision', ['coordinate'], unique=False)
    op.drop_index('ix_business_entity_revision_lat', table_name='business_entity_revision')
    op.drop_index('ix_business_entity_revision_lng', table_name='business_entity_revision')
    op.drop_column('business_entity_revision', 'lng')
    op.drop_column('business_entity_revision', 'lat')


def downgrade():
    op.add_column('business_entity_revision', sa.Column('lat', sa.NUMERIC(precision=15, scale=0), autoincrement=False, nullable=False))
    op.add_column('business_entity_revision', sa.Column('lng', sa.NUMERIC(precision=15, scale=0), autoincrement=False, nullable=False))
    op.create_index('ix_business_entity_revision_lng', 'business_entity_revision', ['lng'], unique=False)
    op.create_index('ix_business_entity_revision_lat', 'business_entity_revision', ['lat'], unique=False)
    op.drop_index('ix_business_entity_revision_coordinate', table_name='business_entity_revision')
    op.drop_column('business_entity_revision', 'coordinate')

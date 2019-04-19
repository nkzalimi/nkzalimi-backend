"""Allow multiple attachments to a request

Revision ID: 4ae1d69d65ff
Revises: 60462ac53829
Create Date: 2019-04-19 12:44:16.306943

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = '4ae1d69d65ff'
down_revision = '60462ac53829'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'attachment', sa.Column('index', sa.Integer(), nullable=False)
    )
    op.add_column(
        'attachment', sa.Column('request_id', UUIDType, nullable=False)
    )
    op.create_index(op.f('ix_attachment_request_id'), 'attachment', ['request_id'], unique=False)
    op.drop_constraint('fk_attachment_id', 'attachment', type_='foreignkey')
    op.create_foreign_key(None, 'attachment', 'request', ['request_id'], ['id'])
    op.drop_column('attachment', 'id')


def downgrade():
    op.add_column('attachment', sa.Column('id', UUIDType, autoincrement=False, nullable=False))
    op.drop_constraint(None, 'attachment', type_='foreignkey')
    op.create_foreign_key('fk_attachment_id', 'attachment', 'request', ['id'], ['id'])
    op.drop_index(op.f('ix_attachment_request_id'), table_name='attachment')
    op.drop_column('attachment', 'request_id')
    op.drop_column('attachment', 'index')

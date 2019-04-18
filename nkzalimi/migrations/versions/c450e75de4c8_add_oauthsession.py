"""Add OAuthSession

Revision ID: c450e75de4c8
Revises: ae4cb6578bed
Create Date: 2019-04-18 21:40:09.561064

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utc import UtcDateTime


# revision identifiers, used by Alembic.
revision = 'c450e75de4c8'
down_revision = 'ae4cb6578bed'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'oauth_session',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('secret', sa.String(), nullable=False),
        sa.Column('created_at', UtcDateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('oauth_session')

"""drop id and name from ical_feeds

Revision ID: 8803050aa66a
Revises: 6ac39abac025
Create Date: 2026-10-29 20:15:09.242958

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8803050aa66a'
down_revision = '6ac39abac025'
branch_labels = None
depends_on = None


def upgrade():
    # Dropping id also drops the primary key it was the only column of
    op.drop_column('ical_feeds', 'id')
    op.drop_column('ical_feeds', 'name')
    op.alter_column('ical_feeds', 'url',
           existing_type=mysql.VARCHAR(length=2048),
           type_=sa.String(length=768),
           existing_nullable=False)
    # Alembic autogenerate doesn't detect primary key changes, so this is added by hand
    op.create_primary_key('pk_ical_feeds', 'ical_feeds', ['url'])


def downgrade():
    op.drop_constraint('PRIMARY', 'ical_feeds', type_='primary')
    op.alter_column('ical_feeds', 'url',
           existing_type=sa.String(length=768),
           type_=mysql.VARCHAR(length=2048),
           existing_nullable=False)
    # MySQL requires an AUTO_INCREMENT column to be a key in the same statement
    op.execute('ALTER TABLE ical_feeds ADD COLUMN id INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST')
    op.add_column('ical_feeds', sa.Column('name', mysql.VARCHAR(length=100), nullable=False, server_default=''))

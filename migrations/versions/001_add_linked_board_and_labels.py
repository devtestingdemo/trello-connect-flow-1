"""Add linked board tracking and label ID/name fields

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add linked board tracking to User model
    op.add_column('users', sa.Column('linked_board_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('linked_board_name', sa.String(), nullable=True))
    
    # Add label_id and label_name to webhook_settings
    op.add_column('webhook_settings', sa.Column('label_id', sa.String(), nullable=True))
    op.add_column('webhook_settings', sa.Column('label_name', sa.String(), nullable=True))
    
    # Add label_id and label_name to user_webhook_preferences
    op.add_column('user_webhook_preferences', sa.Column('label_id', sa.String(), nullable=True))
    op.add_column('user_webhook_preferences', sa.Column('label_name', sa.String(), nullable=True))


def downgrade():
    # Remove linked board tracking from User model
    op.drop_column('users', 'linked_board_name')
    op.drop_column('users', 'linked_board_id')
    
    # Remove label fields from webhook_settings
    op.drop_column('webhook_settings', 'label_name')
    op.drop_column('webhook_settings', 'label_id')
    
    # Remove label fields from user_webhook_preferences
    op.drop_column('user_webhook_preferences', 'label_name')
    op.drop_column('user_webhook_preferences', 'label_id') 
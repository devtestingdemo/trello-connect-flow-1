#!/usr/bin/env python3
"""
Migration script to backfill label_id and label_name fields for existing webhook settings.

This script:
1. Finds all webhook settings that have a 'label' but no 'label_id'
2. Fetches labels from the user's linked board
3. Maps the label name to label ID and updates the database
4. Handles cases where labels no longer exist or users don't have linked boards

Usage:
    python3 backend/migrate_labels.py
"""

import os
import sys
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Add the backend directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import db, User, WebhookSetting, UserWebhookPreference
from app_factory import create_app

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trello_labels(user, board_id):
    """Fetch labels from Trello for a given board"""
    try:
        labels_url = f"https://api.trello.com/1/boards/{board_id}/labels?key={user.apiKey}&token={user.token}"
        resp = requests.get(labels_url, timeout=10)
        
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch labels for board {board_id}: {resp.status_code}")
            return []
        
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching labels for board {board_id}: {e}")
        return []

def migrate_webhook_settings():
    """Migrate webhook settings to include label_id and label_name"""
    app = create_app()
    
    with app.app_context():
        # Initialize database
        db.init_app(app)
        
        # Get all webhook settings that have a label but no label_id
        webhook_settings = WebhookSetting.query.filter(
            WebhookSetting.label.isnot(None),
            WebhookSetting.label != '',
            (WebhookSetting.label_id.is_(None) | (WebhookSetting.label_id == ''))
        ).all()
        
        logger.info(f"Found {len(webhook_settings)} webhook settings to migrate")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for setting in webhook_settings:
            try:
                # Get the user
                user = User.query.filter_by(email=setting.user_email).first()
                if not user:
                    logger.warning(f"User {setting.user_email} not found, skipping setting {setting.id}")
                    skipped_count += 1
                    continue
                
                # Check if user has linked board
                if not user.linked_board_id:
                    logger.warning(f"User {setting.user_email} has no linked board, skipping setting {setting.id}")
                    skipped_count += 1
                    continue
                
                # Check if user has Trello credentials
                if not user.apiKey or not user.token:
                    logger.warning(f"User {setting.user_email} has no Trello credentials, skipping setting {setting.id}")
                    skipped_count += 1
                    continue
                
                # Fetch labels from Trello
                labels = get_trello_labels(user, user.linked_board_id)
                
                # Find matching label
                matching_label = None
                for label in labels:
                    if label.get('name') == setting.label:
                        matching_label = label
                        break
                
                if matching_label:
                    # Update the setting with label_id and label_name
                    setting.label_id = matching_label.get('id')
                    setting.label_name = matching_label.get('name', setting.label)
                    
                    logger.info(f"Migrated setting {setting.id}: label '{setting.label}' -> ID '{setting.label_id}'")
                    migrated_count += 1
                else:
                    logger.warning(f"Label '{setting.label}' not found on board {user.linked_board_id} for setting {setting.id}")
                    # Still update with the name we have, but no ID
                    setting.label_name = setting.label
                    skipped_count += 1
                
            except Exception as e:
                logger.error(f"Error migrating setting {setting.id}: {e}")
                error_count += 1
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Migration completed: {migrated_count} migrated, {skipped_count} skipped, {error_count} errors")
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            db.session.rollback()

def migrate_user_webhook_preferences():
    """Migrate user webhook preferences to include label_id and label_name"""
    app = create_app()
    
    with app.app_context():
        # Initialize database
        db.init_app(app)
        
        # Get all user webhook preferences that have a label but no label_id
        preferences = UserWebhookPreference.query.filter(
            UserWebhookPreference.label.isnot(None),
            UserWebhookPreference.label != '',
            (UserWebhookPreference.label_id.is_(None) | (UserWebhookPreference.label_id == ''))
        ).all()
        
        logger.info(f"Found {len(preferences)} user webhook preferences to migrate")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for preference in preferences:
            try:
                # Get the user
                user = User.query.filter_by(email=preference.user_email).first()
                if not user:
                    logger.warning(f"User {preference.user_email} not found, skipping preference {preference.id}")
                    skipped_count += 1
                    continue
                
                # Check if user has linked board
                if not user.linked_board_id:
                    logger.warning(f"User {preference.user_email} has no linked board, skipping preference {preference.id}")
                    skipped_count += 1
                    continue
                
                # Check if user has Trello credentials
                if not user.apiKey or not user.token:
                    logger.warning(f"User {preference.user_email} has no Trello credentials, skipping preference {preference.id}")
                    skipped_count += 1
                    continue
                
                # Fetch labels from Trello
                labels = get_trello_labels(user, user.linked_board_id)
                
                # Find matching label
                matching_label = None
                for label in labels:
                    if label.get('name') == preference.label:
                        matching_label = label
                        break
                
                if matching_label:
                    # Update the preference with label_id and label_name
                    preference.label_id = matching_label.get('id')
                    preference.label_name = matching_label.get('name', preference.label)
                    
                    logger.info(f"Migrated preference {preference.id}: label '{preference.label}' -> ID '{preference.label_id}'")
                    migrated_count += 1
                else:
                    logger.warning(f"Label '{preference.label}' not found on board {user.linked_board_id} for preference {preference.id}")
                    # Still update with the name we have, but no ID
                    preference.label_name = preference.label
                    skipped_count += 1
                
            except Exception as e:
                logger.error(f"Error migrating preference {preference.id}: {e}")
                error_count += 1
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"User preferences migration completed: {migrated_count} migrated, {skipped_count} skipped, {error_count} errors")
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            db.session.rollback()

def main():
    """Main migration function"""
    logger.info("Starting label migration...")
    
    try:
        # Migrate webhook settings
        migrate_webhook_settings()
        
        # Migrate user webhook preferences
        migrate_user_webhook_preferences()
        
        logger.info("Label migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
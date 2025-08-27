#!/usr/bin/env python3
"""
Manual migration script to add label-related columns and backfill data

This script:
1. Adds linked_board_id and linked_board_name to users table
2. Adds label_id and label_name to webhook_settings and user_webhook_preferences tables
3. Backfills existing label data with IDs from Trello API
4. Handles cases where labels no longer exist or users don't have linked boards

Usage:
    python3 backend/migrate_labels.py
"""

import sqlite3
import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trello_labels(api_key, token, board_id):
    """Fetch labels from Trello for a given board"""
    try:
        labels_url = f"https://api.trello.com/1/boards/{board_id}/labels?key={api_key}&token={token}"
        resp = requests.get(labels_url, timeout=10)
        
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch labels for board {board_id}: {resp.status_code}")
            return []
        
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching labels for board {board_id}: {e}")
        return []

def add_columns():
    """Add the new columns to the database tables"""
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'users.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(webhook_settings)")
        webhook_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(user_webhook_preferences)")
        preference_columns = [col[1] for col in cursor.fetchall()]
        
        # Add linked_board_id and linked_board_name to users table
        if 'linked_board_id' not in user_columns:
            logger.info("Adding linked_board_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN linked_board_id TEXT")
        
        if 'linked_board_name' not in user_columns:
            logger.info("Adding linked_board_name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN linked_board_name TEXT")
        
        # Add label_id and label_name to webhook_settings table
        if 'label_id' not in webhook_columns:
            logger.info("Adding label_id column to webhook_settings table...")
            cursor.execute("ALTER TABLE webhook_settings ADD COLUMN label_id TEXT")
        
        if 'label_name' not in webhook_columns:
            logger.info("Adding label_name column to webhook_settings table...")
            cursor.execute("ALTER TABLE webhook_settings ADD COLUMN label_name TEXT")
        
        # Add label_id and label_name to user_webhook_preferences table
        if 'label_id' not in preference_columns:
            logger.info("Adding label_id column to user_webhook_preferences table...")
            cursor.execute("ALTER TABLE user_webhook_preferences ADD COLUMN label_id TEXT")
        
        if 'label_name' not in preference_columns:
            logger.info("Adding label_name column to user_webhook_preferences table...")
            cursor.execute("ALTER TABLE user_webhook_preferences ADD COLUMN label_name TEXT")
        
        conn.commit()
        logger.info("Column migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Column migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def backfill_labels():
    """Backfill existing label data with IDs from Trello API"""
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'users.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all webhook settings that have a label but no label_id
        cursor.execute("""
            SELECT id, user_email, label, label_id, label_name 
            FROM webhook_settings 
            WHERE label IS NOT NULL AND label != '' AND (label_id IS NULL OR label_id = '')
        """)
        webhook_settings = cursor.fetchall()
        
        logger.info(f"Found {len(webhook_settings)} webhook settings to migrate")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for setting in webhook_settings:
            setting_id, user_email, label, label_id, label_name = setting
            
            try:
                # Get user info
                cursor.execute("SELECT apiKey, token, linked_board_id FROM users WHERE email = ?", (user_email,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    logger.warning(f"User {user_email} not found, skipping setting {setting_id}")
                    skipped_count += 1
                    continue
                
                api_key, token, linked_board_id = user_data
                
                if not linked_board_id:
                    logger.warning(f"User {user_email} has no linked board, skipping setting {setting_id}")
                    skipped_count += 1
                    continue
                
                if not api_key or not token:
                    logger.warning(f"User {user_email} has no Trello credentials, skipping setting {setting_id}")
                    skipped_count += 1
                    continue
                
                # Fetch labels from Trello
                labels = get_trello_labels(api_key, token, linked_board_id)
                
                # Find matching label
                matching_label = None
                for label_data in labels:
                    if label_data.get('name') == label:
                        matching_label = label_data
                        break
                
                if matching_label:
                    # Update the setting with label_id and label_name
                    cursor.execute("""
                        UPDATE webhook_settings 
                        SET label_id = ?, label_name = ? 
                        WHERE id = ?
                    """, (matching_label.get('id'), matching_label.get('name', label), setting_id))
                    
                    logger.info(f"Migrated setting {setting_id}: label '{label}' -> ID '{matching_label.get('id')}'")
                    migrated_count += 1
                else:
                    logger.warning(f"Label '{label}' not found on board {linked_board_id} for setting {setting_id}")
                    # Still update with the name we have, but no ID
                    cursor.execute("""
                        UPDATE webhook_settings 
                        SET label_name = ? 
                        WHERE id = ?
                    """, (label, setting_id))
                    skipped_count += 1
                
            except Exception as e:
                logger.error(f"Error migrating setting {setting_id}: {e}")
                error_count += 1
        
        # Also migrate user_webhook_preferences
        cursor.execute("""
            SELECT id, user_email, label, label_id, label_name 
            FROM user_webhook_preferences 
            WHERE label IS NOT NULL AND label != '' AND (label_id IS NULL OR label_id = '')
        """)
        preferences = cursor.fetchall()
        
        logger.info(f"Found {len(preferences)} user webhook preferences to migrate")
        
        for preference in preferences:
            pref_id, user_email, label, label_id, label_name = preference
            
            try:
                # Get user info
                cursor.execute("SELECT apiKey, token, linked_board_id FROM users WHERE email = ?", (user_email,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    logger.warning(f"User {user_email} not found, skipping preference {pref_id}")
                    skipped_count += 1
                    continue
                
                api_key, token, linked_board_id = user_data
                
                if not linked_board_id:
                    logger.warning(f"User {user_email} has no linked board, skipping preference {pref_id}")
                    skipped_count += 1
                    continue
                
                if not api_key or not token:
                    logger.warning(f"User {user_email} has no Trello credentials, skipping preference {pref_id}")
                    skipped_count += 1
                    continue
                
                # Fetch labels from Trello
                labels = get_trello_labels(api_key, token, linked_board_id)
                
                # Find matching label
                matching_label = None
                for label_data in labels:
                    if label_data.get('name') == label:
                        matching_label = label_data
                        break
                
                if matching_label:
                    # Update the preference with label_id and label_name
                    cursor.execute("""
                        UPDATE user_webhook_preferences 
                        SET label_id = ?, label_name = ? 
                        WHERE id = ?
                    """, (matching_label.get('id'), matching_label.get('name', label), pref_id))
                    
                    logger.info(f"Migrated preference {pref_id}: label '{label}' -> ID '{matching_label.get('id')}'")
                    migrated_count += 1
                else:
                    logger.warning(f"Label '{label}' not found on board {linked_board_id} for preference {pref_id}")
                    # Still update with the name we have, but no ID
                    cursor.execute("""
                        UPDATE user_webhook_preferences 
                        SET label_name = ? 
                        WHERE id = ?
                    """, (label, pref_id))
                    skipped_count += 1
                
            except Exception as e:
                logger.error(f"Error migrating preference {pref_id}: {e}")
                error_count += 1
        
        conn.commit()
        logger.info(f"Data migration completed: {migrated_count} migrated, {skipped_count} skipped, {error_count} errors")
        
    except Exception as e:
        logger.error(f"Data migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Main migration function"""
    logger.info("Starting label migration...")
    
    try:
        # Step 1: Add columns
        if not add_columns():
            logger.error("Failed to add columns, aborting migration")
            return
        
        # Step 2: Backfill data
        backfill_labels()
        
        logger.info("Label migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    main() 
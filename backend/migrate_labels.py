#!/usr/bin/env python3
"""
Manual migration script to add label-related columns
"""
import sqlite3
import os

def migrate_labels():
    """Add linked_board_id to users table and label_id/label_name to webhook_settings table"""
    
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'users.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(webhook_settings)")
        webhook_columns = [col[1] for col in cursor.fetchall()]
        
        # Add linked_board_id and linked_board_name to users table
        if 'linked_board_id' not in user_columns:
            print("Adding linked_board_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN linked_board_id TEXT")
        
        if 'linked_board_name' not in user_columns:
            print("Adding linked_board_name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN linked_board_name TEXT")
        
        # Add label_id and label_name to webhook_settings table
        if 'label_id' not in webhook_columns:
            print("Adding label_id column to webhook_settings table...")
            cursor.execute("ALTER TABLE webhook_settings ADD COLUMN label_id TEXT")
        
        if 'label_name' not in webhook_columns:
            print("Adding label_name column to webhook_settings table...")
            cursor.execute("ALTER TABLE webhook_settings ADD COLUMN label_name TEXT")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Show updated schema
        print("\nUpdated schema:")
        cursor.execute("PRAGMA table_info(users)")
        print("Users table columns:", [col[1] for col in cursor.fetchall()])
        
        cursor.execute("PRAGMA table_info(webhook_settings)")
        print("Webhook_settings table columns:", [col[1] for col in cursor.fetchall()])
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_labels() 
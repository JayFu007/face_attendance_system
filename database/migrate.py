import sqlite3
import os
import sys

# Database path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'attendance.db')

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[1] == column_name:
            return True
    return False

def migrate_database():
    """Migrate database to latest schema"""
    print("Starting database migration...")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if database exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Database not initialized. Please run init_db.py first.")
            conn.close()
            sys.exit(1)
        
        # Add role column to users table if it doesn't exist
        if not check_column_exists(cursor, 'users', 'role'):
            print("Adding 'role' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
            conn.commit()
            print("Added 'role' column to users table.")
        
        # Add is_active column to users table if it doesn't exist
        if not check_column_exists(cursor, 'users', 'is_active'):
            print("Adding 'is_active' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
            conn.commit()
            print("Added 'is_active' column to users table.")
        
        # Check if face_encodings table has the correct schema
        cursor.execute("PRAGMA table_info(face_encodings)")
        columns = cursor.fetchall()
        encoding_column_type = None
        for column in columns:
            if column[1] == 'encoding':
                encoding_column_type = column[2]
                break
        
        # If encoding column is not BLOB, we need to recreate the table
        if encoding_column_type != 'BLOB':
            print("Updating face_encodings table schema...")
            
            # Create a backup of the face_encodings table
            cursor.execute("CREATE TABLE IF NOT EXISTS face_encodings_backup AS SELECT * FROM face_encodings")
            
            # Drop the original table
            cursor.execute("DROP TABLE face_encodings")
            
            # Create the table with the correct schema
            cursor.execute('''
            CREATE TABLE face_encodings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                encoding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')
            
            # Note: We can't restore the data because the encoding format has changed
            # from numpy array bytes to pickle serialized data
            
            print("Updated face_encodings table schema. Note: Previous face encodings have been backed up but not restored.")
            print("Users will need to re-register their faces.")
        
        print("Database migration completed successfully.")
    
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()

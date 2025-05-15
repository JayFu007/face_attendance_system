import sqlite3
import os

# Database path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'attendance.db')


def init_database():
    """Initialize database with required tables"""
    print("Initializing database...")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create users table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           student_id
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           name
                           TEXT
                           NOT
                           NULL,
                           email
                           TEXT
                           NOT
                           NULL,
                           password
                           TEXT
                           NOT
                           NULL,
                           registration_date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           role
                           TEXT
                           DEFAULT
                           'student',
                           is_active
                           INTEGER
                           DEFAULT
                           1
                       )
                       ''')

        # Create face_encodings table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS face_encodings
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           encoding
                           BLOB
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        # Create attendance table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS attendance
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           check_in_time
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           check_out_time
                           TIMESTAMP,
                           status
                           TEXT
                           DEFAULT
                           'present',
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        # Create courses table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS courses
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           course_code
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           course_name
                           TEXT
                           NOT
                           NULL,
                           instructor
                           TEXT
                           NOT
                           NULL,
                           schedule
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Create course_enrollments table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS course_enrollments
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           course_id
                           INTEGER
                           NOT
                           NULL,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           enrollment_date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           course_id
                       ) REFERENCES courses
                       (
                           id
                       ) ON DELETE CASCADE,
                           FOREIGN KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       )
                         ON DELETE CASCADE,
                           UNIQUE
                       (
                           course_id,
                           user_id
                       )
                           )
                       ''')

        # Create course_attendance table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS course_attendance
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           course_id
                           INTEGER
                           NOT
                           NULL,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           attendance_date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           status
                           TEXT
                           DEFAULT
                           'present',
                           FOREIGN
                           KEY
                       (
                           course_id
                       ) REFERENCES courses
                       (
                           id
                       ) ON DELETE CASCADE,
                           FOREIGN KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       )
                         ON DELETE CASCADE
                           )
                       ''')

        # Create admin user if not exists
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        if not cursor.fetchone():
            import hashlib
            admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute('''
                           INSERT INTO users (student_id, name, email, password, role)
                           VALUES (?, ?, ?, ?, ?)
                           ''', ('admin', 'System Administrator', 'admin@example.com', admin_password, 'admin'))
            print("Created default admin user (student_id: admin, password: admin123)")

        conn.commit()
        print("Database initialized successfully.")

    except Exception as e:
        print(f"Error during initialization: {e}")
        conn.rollback()

    finally:
        conn.close()


if __name__ == '__main__':
    init_database()

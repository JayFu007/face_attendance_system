import sqlite3
import os
import numpy as np
import hashlib
import pickle
from datetime import datetime

# Database path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'attendance.db')

class User:
    """User model for handling user-related database operations"""
    
    @staticmethod
    def create_user(student_id, name, email, password):
        """Create a new user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor.execute('''
            INSERT INTO users (student_id, name, email, password)
            VALUES (?, ?, ?, ?)
            ''', (student_id, name, email, hashed_password))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, student_id, name, email, registration_date, role, is_active
        FROM users
        WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'student_id': user[1],
                'name': user[2],
                'email': user[3],
                'registration_date': user[4],
                'role': user[5] if len(user) > 5 else 'student',
                'is_active': bool(user[6]) if len(user) > 6 else True
            }
        return None
    
    @staticmethod
    def get_user_by_student_id(student_id):
        """Get user by student ID"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, student_id, name, email, registration_date, role, is_active
        FROM users
        WHERE student_id = ?
        ''', (student_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'student_id': user[1],
                'name': user[2],
                'email': user[3],
                'registration_date': user[4],
                'role': user[5] if len(user) > 5 else 'student',
                'is_active': bool(user[6]) if len(user) > 6 else True
            }
        return None
    
    @staticmethod
    def authenticate(student_id, password):
        """Authenticate a user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
        SELECT id, student_id, name, email, registration_date, role, is_active
        FROM users
        WHERE student_id = ? AND password = ?
        ''', (student_id, hashed_password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'student_id': user[1],
                'name': user[2],
                'email': user[3],
                'registration_date': user[4],
                'role': user[5] if len(user) > 5 else 'student',
                'is_active': bool(user[6]) if len(user) > 6 else True
            }
        return None
    
    @staticmethod
    def get_all_users(page=1, per_page=10):
        """Get all users"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        cursor.execute('''
        SELECT id, student_id, name, email, registration_date, role, is_active
        FROM users
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        users = cursor.fetchall()
        conn.close()
        
        result = []
        for user in users:
            result.append({
                'id': user[0],
                'student_id': user[1],
                'name': user[2],
                'email': user[3],
                'registration_date': user[4],
                'role': user[5] if len(user) > 5 else 'student',
                'is_active': bool(user[6]) if len(user) > 6 else True
            })
        
        return result
    
    @staticmethod
    def count_all_users():
        """Count all users"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*)
        FROM users
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    @staticmethod
    def search_users(query, page=1, per_page=10):
        """Search users"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        search_query = f"%{query}%"
        cursor.execute('''
        SELECT id, student_id, name, email, registration_date, role, is_active
        FROM users
        WHERE student_id LIKE ? OR name LIKE ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        ''', (search_query, search_query, per_page, offset))
        
        users = cursor.fetchall()
        conn.close()
        
        result = []
        for user in users:
            result.append({
                'id': user[0],
                'student_id': user[1],
                'name': user[2],
                'email': user[3],
                'registration_date': user[4],
                'role': user[5] if len(user) > 5 else 'student',
                'is_active': bool(user[6]) if len(user) > 6 else True
            })
        
        return result
    
    @staticmethod
    def count_search_results(query):
        """Count search results"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        search_query = f"%{query}%"
        cursor.execute('''
        SELECT COUNT(*)
        FROM users
        WHERE student_id LIKE ? OR name LIKE ?
        ''', (search_query, search_query))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    @staticmethod
    def update_user(user_id, student_id, name, email, password=None, role='student', is_active=True):
        """Update user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if password:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute('''
                UPDATE users
                SET student_id = ?, name = ?, email = ?, password = ?, role = ?, is_active = ?
                WHERE id = ?
                ''', (student_id, name, email, hashed_password, role, is_active, user_id))
            else:
                cursor.execute('''
                UPDATE users
                SET student_id = ?, name = ?, email = ?, role = ?, is_active = ?
                WHERE id = ?
                ''', (student_id, name, email, role, is_active, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id):
        """Delete user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Delete user's face encodings
            cursor.execute('''
            DELETE FROM face_encodings
            WHERE user_id = ?
            ''', (user_id,))
            
            # Delete user's attendance records
            cursor.execute('''
            DELETE FROM attendance
            WHERE user_id = ?
            ''', (user_id,))
            
            # Delete user
            cursor.execute('''
            DELETE FROM users
            WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

class FaceEncoding:
    """Face encoding model for handling face-related database operations"""
    
    @staticmethod
    def save_face_encoding(user_id, face_encoding):
        """Save a face encoding for a user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Convert numpy array to bytes for storage
        encoding_bytes = pickle.dumps(face_encoding)
        
        cursor.execute('''
        INSERT INTO face_encodings (user_id, encoding)
        VALUES (?, ?)
        ''', (user_id, encoding_bytes))
        
        conn.commit()
        encoding_id = cursor.lastrowid
        conn.close()
        
        return encoding_id
    
    @staticmethod
    def get_face_encodings_by_user_id(user_id):
        """Get face encodings for a specific user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, user_id, encoding
        FROM face_encodings
        WHERE user_id = ?
        ''', (user_id,))
        
        encodings = cursor.fetchall()
        conn.close()
        
        result = []
        for encoding in encodings:
            # Convert bytes back to numpy array
            face_encoding = pickle.loads(encoding[2])
            result.append({
                'id': encoding[0],
                'user_id': encoding[1],
                'encoding': face_encoding
            })
        
        return result
    
    @staticmethod
    def get_all_face_encodings():
        """Get all face encodings with user information"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT f.id, f.user_id, f.encoding, u.student_id, u.name
        FROM face_encodings f
        JOIN users u ON f.user_id = u.id
        ''')
        
        encodings = cursor.fetchall()
        conn.close()
        
        result = []
        for encoding in encodings:
            # Convert bytes back to numpy array
            face_encoding = pickle.loads(encoding[2])
            result.append({
                'id': encoding[0],
                'user_id': encoding[1],
                'encoding': face_encoding,
                'student_id': encoding[3],
                'name': encoding[4]
            })
        
        return result
    
    @staticmethod
    def delete_face_encodings_by_user_id(user_id):
        """Delete face encodings for a specific user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            DELETE FROM face_encodings
            WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting face encodings: {e}")
            return False

class Attendance:
    """Attendance model for handling attendance-related database operations"""
    
    @staticmethod
    def record_check_in(user_id):
        """Record attendance check-in"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check if user already checked in today
        cursor.execute('''
        SELECT id FROM attendance
        WHERE user_id = ? AND date = ? AND check_out_time IS NULL
        ''', (user_id, today))
        
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return False
        
        cursor.execute('''
        INSERT INTO attendance (user_id, date)
        VALUES (?, ?)
        ''', (user_id, today))
        
        conn.commit()
        attendance_id = cursor.lastrowid
        conn.close()
        
        return attendance_id
    
    @staticmethod
    def record_check_out(user_id):
        """Record attendance check-out"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        UPDATE attendance
        SET check_out_time = ?
        WHERE user_id = ? AND date = ? AND check_out_time IS NULL
        ''', (now, user_id, today))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    @staticmethod
    def get_attendance_by_date(date):
        """Get attendance records for a specific date"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT a.id, a.user_id, u.student_id, u.name, a.check_in_time, a.check_out_time
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.date = ?
        ORDER BY a.check_in_time DESC
        ''', (date,))
        
        records = cursor.fetchall()
        conn.close()
        
        result = []
        for record in records:
            result.append({
                'id': record[0],
                'user_id': record[1],
                'student_id': record[2],
                'name': record[3],
                'check_in_time': record[4],
                'check_out_time': record[5]
            })
        
        return result
    
    @staticmethod
    def get_attendance_by_user(user_id):
        """Get attendance records for a specific user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, date, check_in_time, check_out_time
        FROM attendance
        WHERE user_id = ?
        ORDER BY date DESC, check_in_time DESC
        ''', (user_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        result = []
        for record in records:
            result.append({
                'id': record[0],
                'date': record[1],
                'check_in_time': record[2],
                'check_out_time': record[3]
            })
        
        return result
    
    @staticmethod
    def get_today_attendance(user_id):
        """Get user's attendance for today"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get today's date (format: YYYY-MM-DD)
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
        SELECT id, user_id, check_in_time, check_out_time, status
        FROM attendance
        WHERE user_id = ? AND date(check_in_time) = ?
        ''', (user_id, today))
        
        attendance = cursor.fetchone()
        conn.close()
        
        if attendance:
            return {
                'id': attendance[0],
                'user_id': attendance[1],
                'check_in_time': attendance[2],
                'check_out_time': attendance[3],
                'status': attendance[4]
            }
        return None
    
    @staticmethod
    def get_recent_attendance(limit=10):
        """Get recent attendance records"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT a.id, a.user_id, a.check_in_time, a.status, u.student_id, u.name
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.check_in_time DESC
        LIMIT ?
        ''', (limit,))
        
        attendances = cursor.fetchall()
        conn.close()
        
        result = []
        for attendance in attendances:
            result.append({
                'id': attendance[0],
                'user_id': attendance[1],
                'check_in_time': attendance[2],
                'status': attendance[3],
                'student_id': attendance[4],
                'name': attendance[5]
            })
        
        return result

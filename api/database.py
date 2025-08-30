"""
Simple database module for user management.
Uses SQLite for persistent storage.
"""

import sqlite3
import os
from typing import Optional, Dict, Any
from utils.helpers import get_current_timestamp


class UserDatabase:
    """Simple SQLite database for user management."""
    
    def __init__(self, db_path: str = 'users.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    google_id TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklisted_tokens (
                    jti TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO users (id, email, password, first_name, last_name, role, google_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['id'],
                user_data['email'],
                user_data.get('password'),
                user_data['first_name'],
                user_data['last_name'],
                user_data.get('role', 'user'),
                user_data.get('google_id'),
                user_data['created_at']
            ))
            conn.commit()
        
        return user_data
    
    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM users WHERE email = ? COLLATE NOCASE',
                (email,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Find user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM users WHERE id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def user_exists(self, email: str) -> bool:
        """Check if user exists by email."""
        return self.find_user_by_email(email) is not None
    
    def blacklist_token(self, jti: str) -> None:
        """Blacklist a JWT token."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO blacklisted_tokens (jti, created_at)
                VALUES (?, ?)
            ''', (jti, get_current_timestamp()))
            conn.commit()
    
    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT 1 FROM blacklisted_tokens WHERE jti = ?',
                (jti,)
            )
            return cursor.fetchone() is not None
    
    def cleanup_expired_tokens(self, days: int = 7) -> None:
        """Clean up old blacklisted tokens."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                DELETE FROM blacklisted_tokens 
                WHERE datetime(created_at) < datetime('now', '-{} days')
            '''.format(days))
            conn.commit()


# Global database instance
_db = None

def get_user_db() -> UserDatabase:
    """Get database instance."""
    global _db
    if _db is None:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _db = UserDatabase(db_path)
    return _db

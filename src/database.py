import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

class DatabaseManager:
    def __init__(self, db_path: str = "data/verdicts.db"):
        self.db_path = db_path
        self._ensure_data_directory()
        self._init_database()
        
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create verdicts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_type TEXT,
                    content_hash TEXT,
                    status TEXT DEFAULT 'downloaded'
                )
            ''')
            
            # Create parsed_content table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parsed_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    verdict_id INTEGER,
                    content_type TEXT,
                    content TEXT,
                    parsed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (verdict_id) REFERENCES verdicts (id)
                )
            ''')
            
            # Create analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_type TEXT,
                    analysis_data TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
    def insert_verdict(self, filename: str, file_path: str, file_size: int = None, 
                      file_type: str = None, content_hash: str = None) -> int:
        """Insert a new verdict record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO verdicts (filename, file_path, file_size, file_type, content_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, file_path, file_size, file_type, content_hash))
            conn.commit()
            return cursor.lastrowid
            
    def insert_parsed_content(self, verdict_id: int, content_type: str, content: str):
        """Insert parsed content for a verdict"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO parsed_content (verdict_id, content_type, content)
                VALUES (?, ?, ?)
            ''', (verdict_id, content_type, content))
            conn.commit()
            
    def insert_analytics(self, analysis_type: str, analysis_data: str):
        """Insert analytics results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analytics (analysis_type, analysis_data)
                VALUES (?, ?)
            ''', (analysis_type, analysis_data))
            conn.commit()
            
    def get_all_verdicts(self) -> List[Dict[str, Any]]:
        """Get all verdicts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM verdicts ORDER BY download_date DESC')
            return [dict(row) for row in cursor.fetchall()]
            
    def get_verdict_by_id(self, verdict_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific verdict by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM verdicts WHERE id = ?', (verdict_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
    def get_parsed_content(self, verdict_id: int) -> List[Dict[str, Any]]:
        """Get parsed content for a specific verdict"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM parsed_content WHERE verdict_id = ?', (verdict_id,))
            return [dict(row) for row in cursor.fetchall()]
            
    def get_analytics(self, analysis_type: str = None) -> List[Dict[str, Any]]:
        """Get analytics results"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if analysis_type:
                cursor.execute('SELECT * FROM analytics WHERE analysis_type = ? ORDER BY created_date DESC', (analysis_type,))
            else:
                cursor.execute('SELECT * FROM analytics ORDER BY created_date DESC')
            return [dict(row) for row in cursor.fetchall()]
            
    def get_file_type_stats(self) -> Dict[str, int]:
        """Get statistics by file type"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_type, COUNT(*) as count 
                FROM verdicts 
                WHERE file_type IS NOT NULL 
                GROUP BY file_type
            ''')
            return dict(cursor.fetchall())
            
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as total FROM verdicts')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as parsed FROM parsed_content')
            parsed = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(file_size) as total_size FROM verdicts WHERE file_size IS NOT NULL')
            total_size = cursor.fetchone()[0] or 0
            
            return {
                'total_files': total,
                'parsed_files': parsed,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            } 
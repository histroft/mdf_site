import sqlite3
from contextlib import contextmanager
from typing import Generator
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Контекстный менеджер для соединения с БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Выполнение запроса с автоматическим закрытием соединения"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple) -> int:
        """Выполнение вставки с возвратом ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid
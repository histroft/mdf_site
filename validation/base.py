"""
Базовые классы и константы для модулей проверки
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# Константы
STANDARD_VARIANT_MARKER = '#777'
DEFAULT_VARIANT_MARKER = '#777'

class CheckResult:
    """Результат проверки"""
    
    def __init__(self, success: bool, message: str = "", details: Optional[Dict] = None, problem_fields: Optional[List[str]] = None):
        self.success = success
        self.message = message
        self.details = details or {}
        self.problem_fields = problem_fields or []
    
    def __bool__(self):
        return self.success
    
    def __repr__(self):
        return f"CheckResult(success={self.success}, message='{self.message}', problem_fields={self.problem_fields})"
    
    @classmethod
    def ok(cls, message: str = "", details: Optional[Dict] = None):
        """Создает успешный результат"""
        return cls(True, message, details)
    
    @classmethod
    def fail(cls, message: str = "", details: Optional[Dict] = None, problem_fields: Optional[List[str]] = None):
        """Создает неуспешный результат"""
        return cls(False, message, details, problem_fields)


class BaseChecker:
    """Базовый класс для всех проверок"""
    
    def __init__(self, db: DatabaseConnection):
        """
        Args:
            db: экземпляр DatabaseConnection для работы с БД
        """
        self.db = db
    
    def _get_property_id(self, property_name: str) -> Optional[int]:
        """Получает ID свойства по названию"""
        try:
            result = self.db.execute_query(
                "SELECT property_id FROM properties WHERE property_name = ?",
                (property_name,)
            )
            return result[0]['property_id'] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении ID свойства '{property_name}': {e}")
            return None
    
    def _get_model_id(self, model_name: str) -> Optional[int]:
        """Получает ID модели по названию"""
        try:
            result = self.db.execute_query(
                "SELECT model_id FROM models WHERE model_name = ?",
                (model_name,)
            )
            return result[0]['model_id'] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении ID модели '{model_name}': {e}")
            return None
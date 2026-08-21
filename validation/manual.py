"""
Модуль для проверки ручных разрешений и запретов
"""
import logging
from typing import Dict, Any, Optional
from database.connection import DatabaseConnection
from validation.base import BaseChecker, CheckResult

logger = logging.getLogger(__name__)


class ManualChecker(BaseChecker):
    """Проверяет ручные разрешения и запреты"""
    
    def check_permission(
        self,
        model_name: str,
        prop1: str,
        val1: Any,
        prop2: str,
        val2: Any
    ) -> str:
        """
        Проверяет ручное разрешение/запрет для пары
        
        Returns:
            str: 'allowed', 'forbidden', или 'not_found'
        """
        try:
            # Прямой порядок
            result = self.db.execute_query("""
                SELECT resolution FROM Manual_incomp 
                WHERE model_name = ? 
                AND EXISTS (
                    SELECT 1 FROM properties p1 
                    WHERE p1.property_id = property1_id AND p1.property_name = ?
                )
                AND value1 = ?
                AND EXISTS (
                    SELECT 1 FROM properties p2 
                    WHERE p2.property_id = property2_id AND p2.property_name = ?
                )
                AND value2 = ?
                LIMIT 1
            """, (model_name, prop1, val1, prop2, val2))
            
            if result:
                return 'allowed' if result[0]['resolution'] == 1 else 'forbidden'
            
            # Обратный порядок
            result = self.db.execute_query("""
                SELECT resolution FROM Manual_incomp 
                WHERE model_name = ? 
                AND EXISTS (
                    SELECT 1 FROM properties p1 
                    WHERE p1.property_id = property1_id AND p1.property_name = ?
                )
                AND value1 = ?
                AND EXISTS (
                    SELECT 1 FROM properties p2 
                    WHERE p2.property_id = property2_id AND p2.property_name = ?
                )
                AND value2 = ?
                LIMIT 1
            """, (model_name, prop2, val2, prop1, val1))
            
            if result:
                return 'allowed' if result[0]['resolution'] == 1 else 'forbidden'
            
            return 'not_found'
            
        except Exception as e:
            logger.error(f"Ошибка при проверке ручного разрешения: {e}")
            return 'not_found'
    
    def get_all_manual_rules(self, model_name: Optional[str] = None) -> list:
        """
        Получает все ручные правила
        
        Args:
            model_name: если указано, только для конкретной модели
            
        Returns:
            list: список правил
        """
        try:
            if model_name:
                result = self.db.execute_query("""
                    SELECT m.*, 
                           p1.property_name as prop1_name,
                           p2.property_name as prop2_name
                    FROM Manual_incomp m
                    JOIN properties p1 ON m.property1_id = p1.property_id
                    JOIN properties p2 ON m.property2_id = p2.property_id
                    WHERE m.model_name = ?
                    ORDER BY m.model_name, p1.property_name
                """, (model_name,))
            else:
                result = self.db.execute_query("""
                    SELECT m.*, 
                           p1.property_name as prop1_name,
                           p2.property_name as prop2_name
                    FROM Manual_incomp m
                    JOIN properties p1 ON m.property1_id = p1.property_id
                    JOIN properties p2 ON m.property2_id = p2.property_id
                    ORDER BY m.model_name, p1.property_name
                """)
            
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"Ошибка при получении ручных правил: {e}")
            return []
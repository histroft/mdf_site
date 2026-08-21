"""
Сравнение значений для условий
"""
import logging
from typing import Any
from Economical.constants import PriceConstants, PriceErrors

logger = logging.getLogger(__name__)


class ValueComparator:
    """Сравнение значений"""
    
    @staticmethod
    def to_number(value: Any) -> Any:
        """
        Преобразует значение в число, если возможно
        
        Args:
            value: исходное значение
            
        Returns:
            Any: число или исходное значение
        """
        try:
            if isinstance(value, (int, float)):
                return value
            if '.' in str(value):
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            return value
    
    @staticmethod
    def compare_strings(val1: str, val2: str, operator: str) -> bool:
        """
        Сравнивает строки
        
        Args:
            val1: первая строка
            val2: вторая строка
            operator: оператор сравнения
            
        Returns:
            bool: результат сравнения
        """
        s1 = val1.strip().lower()
        s2 = val2.strip().lower()
        
        if operator in (None, '', PriceConstants.OP_EQUAL):
            return s1 == s2
        if operator == PriceConstants.OP_NOT_EQUAL:
            return s1 != s2
        
        # Для остальных операторов строки сравниваются как числа
        return False
    
    @staticmethod
    def compare_numbers(num1: Any, num2: Any, operator: str) -> bool:
        """
        Сравнивает числа
        
        Args:
            num1: первое число
            num2: второе число
            operator: оператор сравнения
            
        Returns:
            bool: результат сравнения
        """
        try:
            n1 = float(num1)
            n2 = float(num2)
            
            if operator in (None, '', PriceConstants.OP_EQUAL):
                return abs(n1 - n2) < 1e-10  # Допуск для float
            if operator == PriceConstants.OP_NOT_EQUAL:
                return abs(n1 - n2) >= 1e-10
            if operator == PriceConstants.OP_GREATER:
                return n1 > n2
            if operator == PriceConstants.OP_LESS:
                return n1 < n2
            if operator == PriceConstants.OP_GREATER_EQUAL:
                return n1 >= n2
            if operator == PriceConstants.OP_LESS_EQUAL:
                return n1 <= n2
                
        except (ValueError, TypeError):
            return False
        
        return False
    
    @classmethod
    def compare(cls, query_value: Any, condition_value: Any, operator: str) -> bool:
        """
        Сравнивает значения по оператору
        
        Args:
            query_value: значение из запроса
            condition_value: значение из условия
            operator: оператор сравнения
            
        Returns:
            bool: результат сравнения
        """
        try:
            # Определяем тип значений
            qv_str = isinstance(query_value, str)
            cv_str = isinstance(condition_value, str)
            
            # Если оба строки - строковое сравнение
            if qv_str and cv_str:
                return cls.compare_strings(query_value, condition_value, operator)
            
            # Иначе числовое сравнение
            return cls.compare_numbers(query_value, condition_value, operator)
            
        except Exception as e:
            logger.debug(f"{PriceErrors.INVALID_COMPARISON}: {e}")
            return False
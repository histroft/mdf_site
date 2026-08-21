"""
Нормализация данных запроса
"""
import re
from typing import Dict, Any, Optional
from Economical.constants import PriceConstants


class DataNormalizer:
    """Нормализация данных запроса"""
    
    @staticmethod
    def normalize_query(query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует ключи запроса (убирает префиксы 01_, 02_ и т.д.)
        
        Args:
            query: исходный запрос
            
        Returns:
            Dict: запрос с нормализованными ключами
        """
        normalized = {}
        
        
        for key, value in query.items():
            if re.match(PriceConstants.RE_PREFIX_NUM, key):
                normalized_key = key.split('_', 1)[1]
            else:
                normalized_key = key
            normalized[normalized_key] = value
        return normalized
    
    @staticmethod
    def normalize_property_name(prop_name: str) -> str:
        """
        Нормализует название свойства
        
        Args:
            prop_name: исходное название
            
        Returns:
            str: нормализованное название
        """
        prop_name = prop_name.strip().lower()
        if re.match(PriceConstants.RE_PREFIX_NUM, prop_name):
            prop_name = prop_name.split('_', 1)[1]
        return prop_name
    
    @staticmethod
    def find_value_by_key(query: Dict[str, Any], target_key: str) -> Optional[Any]:
        """
        Ищет значение по ключу с учетом нормализации
        
        Args:
            query: словарь запроса
            target_key: искомый ключ
            
        Returns:
            Optional[Any]: значение или None
        """
        target_norm = target_key.lower().strip()
        for key, value in query.items():
            key_norm = key.lower().strip()
            if target_norm == key_norm or target_norm in key_norm:
                return value
        return None
    
    @staticmethod
    def normalize_options(options: list) -> set:
        """
        Нормализует список опций
        
        Args:
            options: список опций
            
        Returns:
            set: множество нормализованных опций
        """
        return {opt.strip().lower() for opt in options if opt}
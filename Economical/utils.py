"""
Вспомогательные функции
"""
import json
from typing import Dict, Any, List
from datetime import datetime


def format_price(price: float) -> str:
    """
    Форматирует цену для отображения
    
    Args:
        price: цена
        
    Returns:
        str: отформатированная строка
    """
    return f"{price:,.2f}".replace(",", " ")


def save_calculation_to_file(
    result: Dict[str, Any],
    filename: Optional[str] = None
) -> str:
    """
    Сохраняет результат расчета в файл
    
    Args:
        result: результат расчета
        filename: имя файла (опционально)
        
    Returns:
        str: путь к сохраненному файлу
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"calculation_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return filename


def parse_price_string(price_str: str) -> float:
    """
    Парсит строку с ценой
    
    Args:
        price_str: строка с ценой
        
    Returns:
        float: число
    """
    # Убираем пробелы и заменяем запятую на точку
    cleaned = price_str.strip().replace(' ', '').replace(',', '.')
    return float(cleaned)
"""
Работа с типами цен
"""
import logging
from typing import List, Optional, Tuple, Dict, Any
from Economical.database import PriceDatabase
from Economical.constants import PriceErrors
from Economical.calculator import calculate_price

logger = logging.getLogger(__name__)


def get_available_price_types(db_path: str, model: str) -> List[str]:
    """
    Получает все доступные типы цен для модели
    
    Args:
        db_path: путь к базе данных
        model: название модели
        
    Returns:
        List[str]: список типов цен
    """
    db = PriceDatabase(db_path)
    return db.get_available_price_types(model)


def select_price_type(
    db_path: str, 
    model: str, 
    preferred_type: Optional[str] = None
) -> str:
    """
    Выбирает подходящий тип цен
    
    Args:
        db_path: путь к базе данных
        model: название модели
        preferred_type: предпочтительный тип
        
    Returns:
        str: выбранный тип цен
        
    Raises:
        ValueError: если нет доступных типов
    """
    available = get_available_price_types(db_path, model)
    
    if not available:
        raise ValueError(PriceErrors.NO_PRICE_TYPES.format(model=model))
    
    if preferred_type and preferred_type in available:
        logger.info(f"Использую предпочтительный тип цен: '{preferred_type}'")
        return preferred_type
    
    logger.info(f"Тип цен '{preferred_type}' не найден, использую первый доступный: '{available[0]}'")
    return available[0]


def calculate_price_with_auto_type(
    db_path: str, 
    query: Dict[str, Any]
) -> Tuple[float, List[str]]:
    """
    Автоматический расчет цены с подбором типа цен
    
    Args:
        db_path: путь к базе данных
        query: запрос с параметрами
        
    Returns:
        Tuple[float, List[str]]: (цена, список сообщений)
    """
    model = query.get('model')
    if not model:
        raise ValueError(PriceErrors.MODEL_KEY_MISSING)
    
    available_types = get_available_price_types(db_path, model)
    
    if not available_types:
        raise ValueError(PriceErrors.NO_PRICE_TYPES.format(model=model))
    
    preferred = query.get('price_type')
    selected_type = select_price_type(db_path, model, preferred)
    
    calculation_query = query.copy()
    calculation_query['price_type'] = selected_type
    
    logger.info(f"Расчет для модели '{model}' с типом цен '{selected_type}'")
    price, messages = calculate_price(db_path, calculation_query)
    
    info_message = f"Автоматически выбран тип цен: '{selected_type}'"
    if preferred and preferred != selected_type:
        info_message += f" (запрошенный '{preferred}' не найден)"
    
    messages.insert(0, info_message)
    messages.insert(1, f"Доступные типы цен: {available_types}")
    
    return price, messages


def validate_price_type(
    db_path: str,
    model: str,
    price_type: str
) -> bool:
    """
    Проверяет, существует ли указанный тип цен для модели
    
    Args:
        db_path: путь к базе данных
        model: название модели
        price_type: проверяемый тип цен
        
    Returns:
        bool: True если тип цен существует
    """
    available = get_available_price_types(db_path, model)
    return price_type in available


def get_price_type_info(
    db_path: str,
    model: str
) -> Dict[str, Any]:
    """
    Получает подробную информацию о типах цен для модели
    
    Args:
        db_path: путь к базе данных
        model: название модели
        
    Returns:
        Dict: информация о типах цен
    """
    db = PriceDatabase(db_path)
    
    return {
        'model': model,
        'available_types': db.get_available_price_types(model),
        'base_price_types': db.get_base_price_types(model),
        'option_price_types': db.get_option_price_types(model),
        'count': len(db.get_available_price_types(model))
    }
"""
Пакет для экономического расчета стоимости дверей
"""
from Economical.calculator import calculate_price
from Economical.price_types import (
    calculate_price_with_auto_type,
    get_available_price_types,
    select_price_type,
    validate_price_type,
    get_price_type_info
)

__all__ = [
    'calculate_price',
    'calculate_price_with_auto_type',
    'get_available_price_types',
    'select_price_type',
    'validate_price_type',
    'get_price_type_info'
]

__version__ = '1.0.0'
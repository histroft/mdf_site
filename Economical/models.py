"""
Модели данных для экономического расчета
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
import sqlite3


@dataclass
class CalculationContext:
    """Контекст расчета"""
    db_path: str
    query: Dict[str, Any]
    price_type: Optional[str] = None
    base_price: float = 0
    total_price: float = 0
    normalized_query: Dict[str, Any] = field(default_factory=dict)
    advance_options: Set[str] = field(default_factory=set)
    messages: List[str] = field(default_factory=list)
    price_changes: List[Dict] = field(default_factory=list)
    cursor: Optional[sqlite3.Cursor] = None
    
    def add_message(self, message: str):
        """Добавляет сообщение"""
        self.messages.append(message)
        print(message)  # Для отладки
    
    def add_price_change(self, change: Dict):
        """Добавляет изменение цены"""
        self.price_changes.append(change)


@dataclass
class BasePrice:
    """Базовая цена модели"""
    price: float
    price_type: str
    nomenclature: str


@dataclass
class AdditionalOption:
    """Дополнительная опция"""
    id: int
    option_id: int
    name: str
    is_percent: bool
    price: float
    price_type: str
    nomenclature: str


@dataclass
class OptionCondition:
    """Условие для опции"""
    condition_id: int
    is_or: bool
    is_not: bool
    condition_text: Optional[str]
    properties: List['ConditionProperty'] = field(default_factory=list)


@dataclass
class ConditionProperty:
    """Свойство условия"""
    property_name: str
    value: str
    comparison_type: str


@dataclass
class CalculationResult:
    """Результат расчета"""
    total_price: float
    messages: List[str]
    base_price: float
    price_type: str
    applied_options: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Преобразует в словарь"""
        return {
            'total_price': self.total_price,
            'base_price': self.base_price,
            'price_type': self.price_type,
            'applied_options': self.applied_options,
            'messages': self.messages
        }
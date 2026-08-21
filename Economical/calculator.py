"""
Основной калькулятор цен (исправленная версия)
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, NamedTuple
from dataclasses import dataclass, field
from functools import lru_cache

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Economical.constants import PriceConstants, PriceErrors
from Economical.models import CalculationContext
from Economical.database import PriceDatabase
from Economical.normalizer import DataNormalizer
from Economical.condition_parser import ConditionParser
from Economical.head_calculator import calculate_head_price

logger = logging.getLogger(__name__)


# ============= ДАТАКЛАССЫ ДЛЯ ТИПИЗАЦИИ =============

class OptionRow(NamedTuple):
    """Структура строки опции из БД"""
    add_opt_id: int
    option_id: str
    name: str
    is_percent_raw: int
    price: float
    opt_price_type: str
    
    @property
    def is_percent(self) -> bool:
        return bool(self.is_percent_raw)


class ConditionRow(NamedTuple):
    """Структура условия из БД"""
    cond_id: int
    cond_or: int
    cond_not: int
    cond_text: str
    
    @property
    def is_or(self) -> bool:
        return bool(self.cond_or)
    
    @property
    def is_not(self) -> bool:
        return bool(self.cond_not)


class ConditionProperty(NamedTuple):
    """Свойство условия"""
    property_name: str
    value: str
    comparison_type: str


@dataclass
class PriceCalculationResult:
    """Результат расчета цены"""
    total_price: float
    base_price: float
    applied_options: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    price_type: str = ""
    
    def add_message(self, msg: str):
        self.messages.append(msg)
    
    def add_option(self, option_name: str, change: float, is_percent: bool, percent_value: Optional[float] = None):
        self.applied_options.append({
            'option': option_name,
            'change': change,
            'is_percent': is_percent,
            'percent_value': percent_value if is_percent else None
        })


def format_price(price: float) -> str:
    """Форматирует цену с разделителем тысяч (русский формат)"""
    if isinstance(price, (int, float)):
        return f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return str(price)


def format_price_change(price: float) -> str:
    """Форматирует изменение цены с знаком +"""
    if price >= 0:
        return f"+{format_price(price)}"
    return format_price(price)


class PriceCalculator:
    """Калькулятор цен (исправленная версия)"""
    
    def __init__(self, db_path: str, debug: bool = False):
        """
        Args:
            db_path: путь к базе данных
            debug: режим отладки (вывод дополнительной информации)
        """
        self.db = PriceDatabase(db_path)
        self.normalizer = DataNormalizer()
        self.debug = debug
    
    def _debug_print(self, *args, **kwargs):
        """Условный вывод отладочной информации"""
        if self.debug:
            print(*args, **kwargs)
    
    def calculate(self, query: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Рассчитывает цену по запросу
        
        Args:
            query: словарь с параметрами запроса
            
        Returns:
            Tuple[float, List[str]]: (итоговая цена, список сообщений)
        """
        result = self.calculate_detailed(query)
        return result.total_price, result.messages
    
    def calculate_detailed(self, query: Dict[str, Any]) -> PriceCalculationResult:
        """
        Рассчитывает цену с детальным результатом
        
        Args:
            query: словарь с параметрами запроса
            
        Returns:
            PriceCalculationResult: детальный результат расчета
        """
        # Валидация входных данных
        if not query.get(PriceConstants.MODEL_KEY):
            result = PriceCalculationResult(0, 0)
            result.add_message("❌ Ошибка: не указана модель")
            return result
        
        context = CalculationContext(
            db_path=self.db.db_path,
            query=query
        )
        
        try:
            # Нормализация данных
            context.normalized_query = self.normalizer.normalize_query(query)
            context.price_type = query.get(PriceConstants.PRICE_TYPE_KEY)
            base_percent = float(query.get(PriceConstants.PERCENT_KEY, 0))
            
            # Получаем дополнительные опции (выбранные пользователем)
            context.advance_options = self._get_normalized_options(context)
            
            context.add_message(f"📋 Запрашиваемый тип цен: {context.price_type}")
            if self.debug:
                context.add_message(f"🔧 Дополнительные опции: {context.advance_options}")
            
            model = context.normalized_query.get(PriceConstants.MODEL_KEY)
            
            # Получаем базовую цену
            start_price, actual_price_type = self.db.get_base_price(
                model, context.price_type
            )
            
            if start_price == 0:
                context.add_message(f"⚠️ Внимание: базовая цена для модели '{model}' не найдена")
            
            context.base_price = round(start_price * (1 + base_percent / 100), 2)
            context.total_price = context.base_price
            
            # Форматированная цена модели
            base_price_formatted = format_price(context.base_price)
            context.add_message(
                f"💰 Цена модели '{model}' (тип: '{actual_price_type}'): {base_price_formatted}"
            )
            if base_percent != 0:
                context.add_message(f"   Наценка: {base_percent:.1f}%")
            
            # Получаем дополнительные опции из БД
            options = self.db.get_additional_options(model, context.price_type)
            self._debug_print(f"\n📋 ЗАГРУЖЕНО ОПЦИЙ: {len(options)}")
            
            # Обрабатываем каждую опцию
            for option_row in options:
                self._process_option(context, OptionRow(*option_row))
            
            # Рассчитываем стоимость надставки
            head_price, head_messages = calculate_head_price(self.db.db_path, query)
            
            if head_price > 0:
                context.total_price += head_price
                context.messages.extend(head_messages)
                context.add_message(f"\n🏗️ Стоимость надставки: +{format_price(head_price)}")
            
            # Итог с форматированием
            total_price_formatted = format_price(context.total_price)
            base_price_formatted = format_price(context.base_price)
            
            context.add_message(f"\n{PriceConstants.SEPARATOR_LINE}")
            context.add_message(f"💰 ИТОГОВАЯ ЦЕНА: {total_price_formatted}")
            context.add_message(f"📊 Базовая цена: {base_price_formatted}")
            context.add_message(f"🏷️ Тип цен: {actual_price_type}")
            context.add_message(PriceConstants.SEPARATOR_LINE)
            
            # Формируем детальный результат
            result = PriceCalculationResult(
                total_price=context.total_price,
                base_price=context.base_price,
                messages=context.messages,
                price_type=actual_price_type
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета: {e}", exc_info=True)
            context.add_message(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            return PriceCalculationResult(0, 0, messages=context.messages)
    
    def _get_normalized_options(self, context: CalculationContext) -> List[str]:
        """Нормализует список выбранных опций из запроса"""
        # Поддерживаем разные ключи для обратной совместимости
        options = context.normalized_query.get('options', [])
        if not options:
            options = context.normalized_query.get(PriceConstants.OPTIONS_KEY, [])
        
        # Нормализуем каждую опцию
        normalized = []
        for opt in options:
            if isinstance(opt, str):
                normalized.append(opt.strip().lower())
            elif isinstance(opt, dict):
                name = opt.get('name', '')
                normalized.append(name.strip().lower())
        
        return normalized
    
    def _process_option(self, context: CalculationContext, option: OptionRow):
        """
        Обрабатывает одну дополнительную опцию
        
        Args:
            context: контекст расчета
            option: структура опции из БД
        """
        self._debug_print(f"\n🔍 ПРОВЕРКА ОПЦИИ: {option.name}")
        self._debug_print(f"   ID: {option.add_opt_id}, цена: {option.price}, процент: {option.is_percent}")
        
        # Проверяем соответствие типа цен
        if context.price_type and option.opt_price_type != context.price_type:
            self._debug_print(f"   ❌ Тип цен не совпадает: {option.opt_price_type} != {context.price_type}")
            return
        
        # Получаем условия для опции
        conditions_raw = self.db.get_option_conditions(option.add_opt_id)
        conditions = [ConditionRow(*c) for c in conditions_raw]
        
        self._debug_print(f"   Условий: {len(conditions)}")
        
        # Проверяем, должна ли быть применена опция
        should_apply = self._check_conditions(context, conditions, option.name)
        
        if not conditions:
            # Нет условий - проверяем, выбрана ли опция пользователем
            option_name_norm = option.name.strip().lower()
            should_apply = option_name_norm in context.advance_options
            self._debug_print(f"   Нет условий, опция выбрана: {should_apply}")
        
        if should_apply:
            self._debug_print(f"   ✅ Опция будет применена")
            self._apply_option_price(context, option)
        else:
            self._debug_print(f"   ❌ Опция НЕ будет применена")
    
    def _check_conditions(
        self, 
        context: CalculationContext, 
        conditions: List[ConditionRow],
        option_name: str
    ) -> bool:
        """
        Проверяет условия опции с поддержкой смешанной логики (И/ИЛИ)
        
        Логика:
        - Если есть условие с OR=True, то оно должно выполниться ИЛИ все условия с OR=False
        - AND условия (OR=False) должны выполниться все
        - OR условия (OR=True) - хотя бы одно
        
        Args:
            context: контекст расчета
            conditions: список условий
            option_name: имя опции (для логов)
            
        Returns:
            bool: True если условия выполнены
        """
        if not conditions:
            return False
        
        parser = ConditionParser(context)
        results = []
        
        for condition in conditions:
            # Получаем свойства условия
            properties_raw = self.db.get_condition_properties(condition.cond_id)
            properties = [ConditionProperty(*p) for p in properties_raw]
            
            self._debug_print(f"\n   📋 ПРОВЕРКА УСЛОВИЯ ID {condition.cond_id}:")
            
            # Выводим информацию о свойствах (только в debug режиме)
            if self.debug:
                for prop in properties:
                    clean_name = prop.property_name.split(' (')[0]
                    query_value = context.normalized_query.get(clean_name, '')
                    self._debug_print(f"      {clean_name}: ожидается '{prop.value}', в запросе '{query_value}'")
                    self._debug_print(f"      Равенство: {query_value == prop.value}")
            
            # Проверяем условие
            if condition.cond_text and condition.cond_text.strip():
                condition_met = parser.parse_condition_text(condition.cond_text)
            else:
                condition_met = parser.evaluate_condition_set(
                    condition.cond_id,
                    condition.is_or,
                    condition.is_not,
                    [(p.property_name, p.value, p.comparison_type) for p in properties]
                )
            
            results.append(condition_met)
            
            # Логируем результат
            self._debug_print(f"      Результат проверки: {condition_met} (OR={condition.is_or}, NOT={condition.is_not})")
        
        # Разделяем условия на AND и OR группы
        and_results = []
        or_results = []
        
        for condition, result in zip(conditions, results):
            if condition.is_or:
                or_results.append(result)
            else:
                and_results.append(result)
        
        # Вычисляем итоговый результат
        # AND условия должны выполниться все
        and_met = all(and_results) if and_results else True
        
        # OR условия - хотя бы одно
        or_met = any(or_results) if or_results else True
        
        final_result = and_met and or_met
        
        self._debug_print(f"\n   🎯 Итог по опции '{option_name}':")
        self._debug_print(f"      AND условия ({len(and_results)}): {and_met}")
        self._debug_print(f"      OR условия ({len(or_results)}): {or_met}")
        self._debug_print(f"      РЕЗУЛЬТАТ: {final_result}")
        
        return final_result
    
    def _apply_option_price(
        self,
        context: CalculationContext,
        option: OptionRow
    ) -> float:
        """
        Применяет цену опции к общей стоимости
        
        Args:
            context: контекст расчета
            option: структура опции
            
        Returns:
            float: новая общая цена
        """
        if option.is_percent:
            add_price = context.base_price * option.price / 100
            price_desc = f"{option.price}% от базовой цены ({format_price(context.base_price)})"
        else:
            add_price = option.price
            price_desc = f"фиксированная сумма ({format_price(option.price)})"
        
        old_total = context.total_price
        context.total_price = round(context.total_price + add_price, 2)
        
        if add_price != 0:
            context.add_message(f"\n✅ Опция '{option.name}' применена")
            context.add_message(f"   📐 Тип расчета: {price_desc}")
            context.add_message(f"   💵 Сумма: {format_price_change(add_price)}")
            context.add_message(f"   📊 Цена до опции: {format_price(old_total)}")
            context.add_message(f"   🎯 Цена после опции: {format_price(context.total_price)}")
            
            # Сохраняем информацию о применённой опции
            if hasattr(context, 'applied_options'):
                context.applied_options.append({
                    'option': option.name,
                    'change': add_price,
                    'from': old_total,
                    'to': context.total_price,
                    'is_percent': option.is_percent,
                    'percent_value': option.price if option.is_percent else None
                })
        
        return context.total_price


# ============= УЛУЧШЕННЫЙ КЛАСС PRICE DATABASE =============

class ImprovedPriceDatabase(PriceDatabase):
    """Расширенный класс работы с БД с кэшированием"""
    
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self._cache = {}
    
    @lru_cache(maxsize=128)
    def get_base_price_cached(self, model: str, price_type: str) -> Tuple[float, str]:
        """
        Получает базовую цену с кэшированием
        
        Returns:
            Tuple[float, str]: (цена, использованный_тип_цен)
        """
        return super().get_base_price(model, price_type)
    
    def get_additional_options_cached(self, model: str, price_type: str) -> List[tuple]:
        """Получает опции с кэшированием"""
        cache_key = f"{model}_{price_type}"
        if cache_key not in self._cache:
            self._cache[cache_key] = super().get_additional_options(model, price_type)
        return self._cache[cache_key]
    
    def clear_cache(self):
        """Очищает кэш"""
        self._cache.clear()
        self.get_base_price_cached.cache_clear()


# ============= ФУНКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ =============

def calculate_price(
    db_path: str, 
    query: Dict[str, Any], 
    price_type: Optional[str] = None,
    debug: bool = False
) -> Tuple[float, List[str]]:
    """
    Основная функция для расчета цены
    
    Args:
        db_path: путь к БД
        query: параметры запроса
        price_type: тип цен (опционально)
        debug: режим отладки
    
    Returns:
        Tuple[float, List[str]]: (цена, сообщения)
    """
    if price_type:
        query['price_type'] = price_type
    
    calculator = PriceCalculator(db_path, debug=debug)
    return calculator.calculate(query)


def calculate_price_detailed(
    db_path: str, 
    query: Dict[str, Any], 
    debug: bool = False
) -> PriceCalculationResult:
    """
    Расчёт цены с детальным результатом
    
    Returns:
        PriceCalculationResult: детальный результат
    """
    calculator = PriceCalculator(db_path, debug=debug)
    return calculator.calculate_detailed(query)


if __name__ == '__main__':
    from config import Config
    
    # Тестовые данные
    test_data = {
        'model': 'DELTA 100 MP',
        'price_type': 'РРЦ',
        '01_Ширина': '950',
        '02_Высота': '2300',
        '03_Петли': 'L',
        '04_Лицо (цвет)': 'темно-серый букле графит',
        '05_Лицо (рисунок)': '-',
        '06_Внутр. отделка (цвет)': 'ПВХ Санторини белый',
        '07_Внутр. отделка (рисунок)': 'D36',
        '08_Фурнитура': 'ХКР_БН МОН_ALFA',
        '09_Монтаж': 'НАКЛ',
        '10_Обналичка': '-',
        '11_Обналичка (цвет)': '-',
        'options': [],
        'count': 1,
        'percent_base_price': 0
    }
    
    db_path = Config.NEW_PATH_TO_PRICE_DB
    
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ КАЛЬКУЛЯТОРА ЦЕН")
    print("="*60)
    
    # Детальный расчет с отладкой
    result = calculate_price_detailed(db_path, test_data, debug=True)
    
    print(f"\n{'='*60}")
    print(f"💰 ИТОГОВАЯ ЦЕНА: {format_price(result.total_price)}")
    print(f"📊 Базовая цена: {format_price(result.base_price)}")
    print(f"🏷️ Тип цен: {result.price_type}")
    print(f"📦 Применено опций: {len(result.applied_options)}")
    print(f"{'='*60}\n")
    
    # Выводим все сообщения
    print("📝 ДЕТАЛЬНЫЙ ЛОГ РАСЧЕТА:")
    print("-"*60)
    for msg in result.messages:
        print(msg)
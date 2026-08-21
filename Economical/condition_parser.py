"""
condition_parser.py - с поддержкой текстовых условий 1С
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


def try_convert_num(s):
    """Пробует преобразовать строку в число"""
    try:
        if isinstance(s, (int, float)):
            return s
        if '.' in str(s):
            return float(s)
        else:
            return int(s)
    except (ValueError, TypeError):
        return s


class ConditionParser:
    """Парсер условий для опций с поддержкой разных форматов"""
    
    def __init__(self, context):
        self.context = context
        self.query = context.normalized_query
    
    def _clean_property_name(self, prop_name: str) -> str:
        """Очищает имя свойства от уточнений в скобках"""
        cleaned = re.sub(r'\s*\([^)]*Справочник[^)]*\)', '', prop_name)
        cleaned = re.sub(r'\s*\([^)]*Свойство[^)]*\)', '', cleaned)
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()
    
    def _find_query_value(self, prop_name: str) -> str:
        """Находит значение в запросе по имени свойства"""
        # Прямой поиск
        if prop_name in self.query:
            return str(self.query[prop_name])
        
        # Очищаем имя
        clean_name = self._clean_property_name(prop_name)
        if clean_name in self.query:
            return str(self.query[clean_name])
        
        # Убираем префикс (01_, 02_ и т.д.)
        name_without_prefix = re.sub(r'^\d+_', '', clean_name)
        if name_without_prefix in self.query:
            return str(self.query[name_without_prefix])
        
        # Поиск по окончанию
        for key in self.query.keys():
            if key.endswith(name_without_prefix) or key.endswith(clean_name):
                return str(self.query[key])
        
        # Поиск по вхождению
        name_lower = name_without_prefix.lower()
        for key in self.query.keys():
            if name_lower in key.lower():
                return str(self.query[key])
        
        return ''
    
    def _evaluate_condition(self, prop: str, op: str, val: str) -> bool:
        """Выполняет простое сравнение prop op val по значениям из query"""
        # Нормализуем имя свойства
        query_value = self._find_query_value(prop)
        
        if not query_value and query_value != 0:
            logger.debug(f"  Свойство '{prop}' отсутствует в запросе — условие не выполнено")
            return False
        
        q_val = try_convert_num(query_value)
        c_val = try_convert_num(val)
        
        if op == '>':
            return q_val > c_val
        elif op == '<':
            return q_val < c_val
        elif op == '<>':
            return q_val != c_val
        elif op == '>=':
            return q_val >= c_val
        elif op == '<=':
            return q_val <= c_val
        elif op == '=':
            return q_val == c_val
        else:
            logger.debug(f"  Неизвестный оператор сравнения: {op}")
            return False
    
    def _parse_condition_block(self, block: str) -> bool:
        """
        Проверяет блок связанный 'и' (AND).
        Возвращает True, если все условия внутри выполнены.
        """
        # Убираем скобки
        block = block.strip()
        if block.startswith('(') and block.endswith(')'):
            block = block[1:-1].strip()
        
        # Разбиваем по 'и'
        conditions = re.split(r'\s+и\s+', block, flags=re.IGNORECASE)
        
        logger.debug(f"    Проверяем блок с условиями (AND): {conditions}")
        
        for cond in conditions:
            cond = cond.strip()
            # Ищем оператор сравнения
            m = re.match(r'(.+?)(>=|<=|<>|=|>|<)(.+)', cond)
            if not m:
                logger.debug(f"    Неверный формат условия: '{cond}'")
                return False
            
            prop, op, val = m.group(1).strip(), m.group(2), m.group(3).strip()
            # Проверяем условие
            res = self._evaluate_condition(prop, op, val)
            logger.debug(f"    Условие: {prop} {op} {val} -> {res}")
            if not res:
                return False
        
        return True
    
    def parse_1c_condition(self, condition_text: str) -> bool:
        """
        Парсит условие в формате 1С:
        "Если (Ширина>860 и Ширина<1000 и Ширина<>950 и Высота<=2100) или (Высота>=1900 ...) Тогда УсловиеВыполнено=Истина; КонецЕсли;"
        """
        if not condition_text:
            return False
        
        logger.debug(f"\nПарсинг условного текста:")
        logger.debug(condition_text.strip())
        
        # Извлекаем содержимое между "Если" и "Тогда"
        m = re.search(r'Если\s+(.+?)\s+Тогда', condition_text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            logger.debug("  Не найдено выражение после 'Если' и до 'Тогда'")
            return False
        
        expr = m.group(1).strip()
        
        # Убираем переводы строк и лишние пробелы
        expr = expr.replace('\n', ' ').replace('\r', ' ')
        expr = re.sub(r'\s+', ' ', expr)
        
        # Разбиваем по ключевому слову "или" верхнего уровня
        blocks = re.split(r'(?i)\bили\b', expr)
        
        logger.debug(f"Найдено блоков, соединённых ИЛИ: {len(blocks)}")
        
        for i, block in enumerate(blocks, 1):
            res = self._parse_condition_block(block)
            logger.debug(f"Результат блока {i}: {res}")
            if res:
                logger.debug("Условие выполнено (хотя бы один блок ИЛИ истинный)")
                return True
        
        logger.debug("Все блоки условий не выполнены")
        return False
    
    def evaluate_condition_set(
        self, 
        condition_id: int, 
        is_or: bool, 
        is_not: bool, 
        properties: List[Tuple[str, str, str]]
    ) -> bool:
        """Вычисляет набор условий из структурированных свойств"""
        if not properties:
            return False
        
        results = []
        for prop_name, value, comp_type in properties:
            query_value = self._find_query_value(prop_name)
            condition_value = str(value).strip()
            comp_type = comp_type or '='
            
            logger.debug(f"Сравнение: '{prop_name}' = '{query_value}' vs '{condition_value}' ({comp_type})")
            
            if comp_type == '=' or comp_type == '':
                result = self._compare_equal(query_value, condition_value)
            elif comp_type == '>':
                result = self._compare_greater(query_value, condition_value)
            elif comp_type == '<':
                result = self._compare_less(query_value, condition_value)
            elif comp_type == '>=':
                result = self._compare_greater_equal(query_value, condition_value)
            elif comp_type == '<=':
                result = self._compare_less_equal(query_value, condition_value)
            elif comp_type.lower() == 'contains':
                result = self._compare_contains(query_value, condition_value)
            else:
                logger.warning(f"Неизвестный тип сравнения: {comp_type}")
                result = False
            
            results.append(result)
        
        if is_or:
            final_result = any(results)
        else:
            final_result = all(results)
        
        if is_not:
            final_result = not final_result
        
        return final_result
    
    def parse_condition_text(self, condition_text: str) -> bool:
        """
        Парсит текстовое условие.
        Поддерживает как простые условия, так и формат 1С.
        """
        if not condition_text or not condition_text.strip():
            return False
        
        # Проверяем, является ли условие форматом 1С
        if 'Если' in condition_text and 'Тогда' in condition_text:
            return self.parse_1c_condition(condition_text)
        
        # Простые условия
        patterns = [
            (r'(\w+)\s*>\s*([\d\.]+)', self._compare_greater),
            (r'(\w+)\s*<\s*([\d\.]+)', self._compare_less),
            (r'(\w+)\s*>=\s*([\d\.]+)', self._compare_greater_equal),
            (r'(\w+)\s*<=\s*([\d\.]+)', self._compare_less_equal),
            (r'(\w+)\s*=\s*([^=]+)', self._compare_equal),
            (r'(\w+)\s+contains\s+(.+)', self._compare_contains),
        ]
        
        for pattern, compare_func in patterns:
            match = re.search(pattern, condition_text, re.IGNORECASE)
            if match:
                field = match.group(1).strip()
                value = match.group(2).strip()
                
                if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                    value = value[1:-1]
                
                query_value = self._find_query_value(field)
                return compare_func(query_value, value)
        
        logger.warning(f"Не удалось распарсить условие: {condition_text}")
        return False
    
    def _compare_equal(self, query_value: str, condition_value: str) -> bool:
        """Сравнение на равенство"""
        # Пустое значение в запросе совпадает только с пустым условием
        query_norm = str(query_value).strip().lower() if query_value else ''
        condition_norm = str(condition_value).strip().lower() if condition_value else ''
        
        if not query_norm:
            return not condition_norm
        if not condition_norm:
            return False
        
        return query_norm == condition_norm
    
    def _compare_greater(self, query_value: str, condition_value: str) -> bool:
        try:
            return float(query_value) > float(condition_value)
        except (ValueError, TypeError):
            return False
    
    def _compare_less(self, query_value: str, condition_value: str) -> bool:
        try:
            return float(query_value) < float(condition_value)
        except (ValueError, TypeError):
            return False
    
    def _compare_greater_equal(self, query_value: str, condition_value: str) -> bool:
        try:
            return float(query_value) >= float(condition_value)
        except (ValueError, TypeError):
            return False
    
    def _compare_less_equal(self, query_value: str, condition_value: str) -> bool:
        try:
            return float(query_value) <= float(condition_value)
        except (ValueError, TypeError):
            return False
    
    def _compare_contains(self, query_value: str, condition_value: str) -> bool:
        query_norm = str(query_value).strip().lower()
        condition_norm = str(condition_value).strip().lower()
        return condition_norm in query_norm
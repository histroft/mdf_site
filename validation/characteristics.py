"""Проверка совместимости характеристик"""

from typing import Dict, List, Optional
from database.connection import DatabaseConnection
from validation.base import BaseChecker, CheckResult


class CharacteristicsChecker(BaseChecker):
    """Проверяет совместимость характеристик"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
    
    def check_all(self, model: str, properties: Dict[str, str]) -> CheckResult:
        """Проверяет все характеристики на совместимость"""
        try:
            model_id = self._get_model_id(model)
            if not model_id:
                return CheckResult.fail(f"Модель '{model}' не найдена")
            
            incompatible_pairs = self._find_incompatible_pairs(model_id, properties)
            
            if incompatible_pairs:
    # Собираем проблемные поля из всех несовместимых пар
                problem_fields = []
                details = []
                incompatible_descriptions = []  # для понятного описания
                
                for pair in incompatible_pairs:
                    if pair.get('prop1'):
                        problem_fields.append(pair['prop1'])
                    if pair.get('prop2'):
                        problem_fields.append(pair['prop2'])
                    
                    # Формируем человекочитаемое описание несовместимости
                    incompatible_descriptions.append(
                        f"'{pair['prop1']}={pair['val1']}' несовместимо с '{pair['prop2']}={pair['val2']}'"
                    )
                    
                    # Формируем детальное сообщение
                    details.append(
                        f"Несовместимость: {pair['prop1']}='{pair['val1']}' и {pair['prop2']}='{pair['val2']}'"
                    )
                
                # Убираем дубликаты
                problem_fields = list(set(problem_fields))
                
                # Формируем понятное сообщение с указанием конкретных значений
                if len(incompatible_descriptions) == 1:
                    message = f"Изготовление невозможно: {incompatible_descriptions[0]}"
                else:
                    message = f"Изготовление невозможно. Найдены несовместимые характеристики:\n" + "\n".join(incompatible_descriptions)
                
                return CheckResult.fail(
                    message=message,
                    details={'incompatible_pairs': incompatible_pairs, 'details': details},
                    problem_fields=problem_fields
                )
            
            return CheckResult.ok("Характеристики совместимы")
            
        except Exception as e:
            return CheckResult.fail(f"Ошибка проверки характеристик: {e}")
    
    def _find_incompatible_pairs(self, model_id: int, properties: Dict[str, str]) -> List[Dict]:
        """Находит несовместимые пары характеристик"""
        incompatible_pairs = []
        
        # Получаем ID свойств
        property_ids = self._get_property_ids(list(properties.keys()))
        
        prop_items = list(properties.items())
        for i in range(len(prop_items)):
            for j in range(i + 1, len(prop_items)):
                key1, val1 = prop_items[i]
                key2, val2 = prop_items[j]
                
                prop_id1 = property_ids.get(key1)
                prop_id2 = property_ids.get(key2)
                
                if prop_id1 and prop_id2:
                    # Проверяем несовместимость в обе стороны
                    query = """
                        SELECT * FROM incompatibilities 
                        WHERE model_id = ? 
                        AND ((property1_id = ? AND property2_id = ?) 
                             OR (property1_id = ? AND property2_id = ?))
                        AND value1 = ? AND value2 = ?
                    """
                    results = self.db.execute_query(
                        query, 
                        (model_id, prop_id1, prop_id2, prop_id2, prop_id1, val1, val2)
                    )
                    
                    for row in results:
                        incompatible_pairs.append({
                            'prop1': key1,
                            'val1': val1,
                            'prop2': key2,
                            'val2': val2,
                            'details': dict(row)
                        })
        
        return incompatible_pairs
    
    def _get_property_ids(self, property_names: List[str]) -> Dict[str, int]:
        """Получает ID свойств по их названиям"""
        if not property_names:
            return {}
        
        placeholders = ','.join(['?'] * len(property_names))
        query = f"SELECT property_id, property_name FROM properties WHERE property_name IN ({placeholders})"
        results = self.db.execute_query(query, tuple(property_names))
        
        return {row['property_name']: row['property_id'] for row in results}
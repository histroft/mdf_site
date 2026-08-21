"""Проверка вариантов модели"""


import sys
from pathlib import Path
from typing import Tuple, Dict, Any, List, Union

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
    
from typing import Dict, Optional, Tuple, List
from database.connection import DatabaseConnection
from validation.base import BaseChecker, CheckResult


class VariantChecker(BaseChecker):
    """Проверяет варианты модели"""
    
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
    
    def check_standard_variant(self, model: str, properties: Dict[str, str]) -> CheckResult:
        """Проверяет, есть ли стандартный вариант (без #777) для заданных свойств"""
        try:
            model_id = self._get_model_id(model)
            if not model_id:
                return CheckResult.fail(f"Модель '{model}' не найдена")
            
            variants = self._get_model_variants(model_id)
            
            matching_variants = []
            for variant in variants:
                unique_comb = variant.get('unique_combination', '')
                if '#777' not in unique_comb:  # Только стандартные варианты
                    if self._check_variant_match(variant, properties):
                        matching_variants.append(variant)
            
            if matching_variants:
                print(f"   ✅ Найдено {len(matching_variants)} стандартных вариантов")
                return CheckResult.ok("Стандартный вариант найден")
            else:
                print(f"   ❌ Стандартные варианты не найдены")
                return CheckResult.fail("Стандартный вариант не найден")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return CheckResult.fail(f"Ошибка проверки стандартного варианта: {e}")
        
        
    #================================================================================
    def find_777_variant(self, model: str, properties: Dict[str, str]) -> CheckResult:
        """Находит вариант с #777 и проверяет, подходят ли свойства"""
        try:
            model_id = self._get_model_id(model)
            if not model_id:
                return CheckResult.fail(f"Модель '{model}' не найдена")
            
            variant = self._get_777_variant(model_id)
            if not variant:
                return CheckResult.fail("Вариант #777 не найден")
            
            is_valid, problem_fields, details = self._check_variant_with_properties(variant, properties)
            
            if is_valid:
                return CheckResult.ok("Вариант #777 найден и совместим")
            else:
                if problem_fields:
                    fields_str = ', '.join(problem_fields)
                    message = f"Вариант #777: несовместимые поля: {fields_str}"
                    if details:
                        message += f". {details[0] if details else ''}"
                    return CheckResult.fail(
                        message=message,
                        details={'incompatible_fields': details},
                        problem_fields=problem_fields
                    )
                return CheckResult.fail("Вариант #777: несовместимые характеристики")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return CheckResult.fail(f"Ошибка поиска варианта #777: {e}")
    #======================================================================================
    
    
    def _get_model_variants(self, model_id: int) -> List[Dict]:
        """Получает все варианты модели"""
        try:
            query = """
                SELECT variant_id, unique_combination 
                FROM variants 
                WHERE model_id = ?
            """
            results = self.db.execute_query(query, (model_id,))
            variants = [dict(row) for row in results]
            
            print(f"   📋 Найдено вариантов для модели: {len(variants)}")
            for v in variants:
                print(f"      ID: {v['variant_id']}, unique: {v['unique_combination']}")
            
            return variants
        except Exception as e:
            print(f"Error getting model variants: {e}")
            return []
    
    def _get_777_variant(self, model_id: int) -> Optional[Dict]:
        """Получает вариант с #777"""
        try:
            query = """
                SELECT variant_id, unique_combination 
                FROM variants 
                WHERE model_id = ? AND unique_combination LIKE '%#777%'
                LIMIT 1
            """
            results = self.db.execute_query(query, (model_id,))
            if results:
                return dict(results[0])
            return None
        except Exception as e:
            print(f"Error getting 777 variant: {e}")
            return None
    
    def _check_variant_match(self, variant: Dict, properties: Dict[str, str]) -> bool:
        """
        Проверяет, соответствуют ли свойства варианту.
        Значение пользователя должно быть в списке допустимых значений варианта.
        """
        try:
            variant_id = variant['variant_id']
            char_query = """
                SELECT p.property_name, c.value 
                FROM characteristics c
                JOIN properties p ON c.property_id = p.property_id
                WHERE c.variant_id = ?
            """
            results = self.db.execute_query(char_query, (variant_id,))
            
            # Собираем допустимые значения для каждого свойства
            allowed_values = {}
            for row in results:
                prop_name = row['property_name']
                value = str(row['value']).strip()
                
                if prop_name not in allowed_values:
                    allowed_values[prop_name] = []
                allowed_values[prop_name].append(value)
            
            print(f"   🎯 Проверка варианта {variant.get('unique_combination', variant_id)}:")
            
            # Проверяем каждое свойство пользователя
            for key, user_value in properties.items():
                if key in allowed_values:
                    if user_value in allowed_values[key]:
                        print(f"      ✅ {key}: '{user_value}' - ДОПУСТИМО")
                    else:
                        print(f"      ❌ {key}: '{user_value}' - НЕ ДОПУСТИМО (допустимо: {allowed_values[key]})")
                        return False
                else:
                    # Свойства нет в варианте - это нормально (опционально)
                    print(f"      ⚠️ {key}: отсутствует в варианте (пропускаем)")
            
            print(f"   ✅ Вариант подходит")
            return True
            
        except Exception as e:
            print(f"Error checking variant match: {e}")
            return False
            
        
        
        
        
        
#============================================================
    def _check_variant_with_properties(self, variant: Dict, properties: Dict[str, str]) -> Tuple[bool, List[str], List[str]]:
        """
        Проверяет, соответствуют ли свойства варианту.
        Возвращает (совместимы_ли, список_проблемных_полей, детали_ошибок)
        """
        problem_fields = []
        details = []
        
        try:
            variant_id = variant['variant_id']
            char_query = """
                SELECT p.property_name, c.value 
                FROM characteristics c
                JOIN properties p ON c.property_id = p.property_id
                WHERE c.variant_id = ?
            """
            results = self.db.execute_query(char_query, (variant_id,))
            
            # Собираем ВСЕ допустимые значения для каждого свойства
            variant_dict = {}
            for row in results:
                prop_name = row['property_name']
                value = str(row['value']).strip()
                
                if prop_name not in variant_dict:
                    variant_dict[prop_name] = []
                variant_dict[prop_name].append(value)
            
            
            
            # Проверяем каждое свойство
            for key, value in properties.items():
                if key in variant_dict:
                    allowed_values = variant_dict[key]
                    
                    # Проверяем, входит ли значение в список допустимых
                    if str(value) not in allowed_values:
                        problem_fields.append(key)
                        details.append(f"{key}='{value}' не входит в допустимые значения: {', '.join(allowed_values)}")
                        print(f"   ❌ {key}='{value}' - НЕДОПУСТИМО (допустимо: {', '.join(allowed_values)})")
                    else:
                        print(f"   ✅ {key}='{value}' - допустимо")
                else:
                    # Если свойства нет в варианте, это не обязательно проблема
                    # Может быть, это дополнительное свойство
                    print(f"   ℹ️ Свойство '{key}' отсутствует в варианте #777 (возможно, дополнительное)")
            
            # Выводим итог
            if problem_fields:
                print(f"\n   ❌ Найдено {len(problem_fields)} несоответствий: {', '.join(problem_fields)}")
            else:
                print(f"\n   ✅ Все свойства соответствуют допустимым значениям")
            
        except Exception as e:
            print(f"Error checking variant properties: {e}")
            import traceback
            traceback.print_exc()
            problem_fields.append('unknown')
            details.append(str(e))
        
        return len(problem_fields) == 0, problem_fields, details
#========================================================================



if __name__ == '__main__':
    c=VariantChecker(DatabaseConnection("database/doors.db"))
    test_data = {
        'model': 'SNEGIR PRO PP',
        '01_Ширина': '950',
        '02_Высота': '2100',
        '03_Петли': 'L',
        '04_Лицо (цвет)': 'ЛКП Графит',
        '05_Лицо (рисунок)': 'S60-NC1',
        '06_Внутр. отделка (цвет)': 'ПВХ Ферро',
        '07_Внутр. отделка (рисунок)': 'S60-NC1',
        '08_Фурнитура': 'ХКР_МОН 3D_ALFA',
        '09_Монтаж': 'НАКЛ',
        '10_Обналичка': 'НУ-1',
        '11_Обналичка (цвет)': 'ЛКП Графит',
        'peep': False,
        'peep_offset': False,
        'adv_lock': True,
        'latch': True,
        'options': []
    }
    print(c.check_standard_variant('SNEGIR PRO PP', test_data))
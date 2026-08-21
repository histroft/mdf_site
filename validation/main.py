import sys
from pathlib import Path
from typing import Tuple, Dict, Any, List, Union

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
from database.connection import DatabaseConnection
from validation.base import CheckResult
from validation.variant import VariantChecker
from validation.characteristics import CharacteristicsChecker
from validation.mdf import MDFChecker
from validation.manual import ManualChecker

# ==================== ЦВЕТА ДЛЯ ТЕРМИНАЛА ====================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Иконки с цветами
    SUCCESS = f"{GREEN}✅{END}"
    ERROR = f"{RED}❌{END}"
    WARNING = f"{YELLOW}⚠️{END}"
    INFO = f"{BLUE}ℹ️{END}"
    DEBUG = f"{CYAN}🔍{END}"

def cprint(text, color='white', bold=False, end='\n'):
    """Цветной print"""
    colors = {
        'red': Colors.RED,
        'green': Colors.GREEN,
        'yellow': Colors.YELLOW,
        'blue': Colors.BLUE,
        'cyan': Colors.CYAN,
        'white': ''
    }
    bold_prefix = Colors.BOLD if bold else ''
    print(f"{bold_prefix}{colors.get(color, '')}{text}{Colors.END}", end=end)

logger = logging.getLogger(__name__)


class DoorManufacturingChecker:
    """Проверяет возможность изготовления двери"""
    
    def __init__(self, doors_db_path: str, mdf_db_path: str):
        self.doors_db = DatabaseConnection(doors_db_path)
        self.mdf_db_path = mdf_db_path
        
        self.variant_checker = VariantChecker(self.doors_db)
        self.characteristics_checker = CharacteristicsChecker(self.doors_db)
        self.mdf_checker = MDFChecker(self.doors_db, self.mdf_db_path)
        self.manual_checker = ManualChecker(self.doors_db)
    
    def _extract_properties(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Извлекает свойства из входных данных"""
        properties = {}
        
        prop_keys = [
            '01_Ширина', '02_Высота', '03_Петли',
            '04_Лицо (цвет)', '05_Лицо (рисунок)',
            '06_Внутр. отделка (цвет)', '07_Внутр. отделка (рисунок)',
            '08_Фурнитура', '09_Монтаж', '10_Обналичка', '11_Обналичка (цвет)'
        ]
        
        for key in prop_keys:
            value = data.get(key)
            if value is not None and value != '-' and value != '':
                properties[key] = str(value)
                
        # ✅ Добавляем данные о надставке
        if data.get('head', False):
            properties['head_type'] = data.get('head_type', 'обычная')
            properties['head_pic_out'] = data.get('head_pic_out', '')
            properties['head_pic_in'] = data.get('head_pic_in', '')
            properties['height_head'] = str(data.get('height_head', 0))
        
        return properties
    
    def check(self, data: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """Проверяет возможность изготовления двери"""
        problem_fields = []
        details = []
        
        try:
            model = data.get('model')
            if not model:
                return False, "Не указана модель", ['model']
            
            properties = self._extract_properties(data)
            
            # Заголовок
            cprint(f"\n{'='*60}", 'cyan', bold=True)
            cprint(f"🔍 ПРОВЕРКА ВОЗМОЖНОСТИ ИЗГОТОВЛЕНИЯ", 'cyan', bold=True)
            cprint(f"{'='*60}", 'cyan', bold=True)
            cprint(f"📦 Модель: {model}", 'blue', bold=True)
            cprint(f"📋 Свойства: {properties}", 'white')
            
            # Шаг 1: Проверяем стандартные варианты
            cprint(f"\n📌 ШАГ 1: Проверка стандартных вариантов...", 'blue', bold=True)
            standard_result = self.variant_checker.check_standard_variant(model, properties)
            if standard_result:
                cprint(f"   ⚠️ Стандартный вариант найден", 'red')
                return False, "Это стандартное исполнение. Сделайте заказ на сайте https://reserve.torex.ru", []
            else:
                cprint(f"   ✅ Стандартный вариант не найден, проверяем вариант #777", 'green')
            
            # Шаг 2: Ищем вариант с #777
            cprint(f"\n📌 ШАГ 2: Поиск варианта #777...", 'blue', bold=True)
            variant_result = self.variant_checker.find_777_variant(model, properties)
            if not variant_result:
                cprint(f"   ❌ Ошибка: {variant_result.message}", 'red')
                if hasattr(variant_result, 'problem_fields') and variant_result.problem_fields:
                    problem_fields.extend(variant_result.problem_fields)
                    cprint(f"   🎯 Проблемные поля: {', '.join(problem_fields)}", 'yellow')
                return False, variant_result.message, problem_fields
            cprint(f"   ✅ Вариант #777 найден и совместим", 'green')
            
            # Шаг 3: Проверка ручных несовместимостей
            cprint(f"\n📌 ШАГ 3: Проверка совместимости РУЧНЫХ характеристик...", 'blue', bold=True)
            manual_problem_fields = []
            
            manual_rules = self.manual_checker.get_all_manual_rules(model)
            
            prop_items = list(properties.items())
            for i in range(len(prop_items)):
                for j in range(i + 1, len(prop_items)):
                    key1, val1 = prop_items[i]
                    key2, val2 = prop_items[j]
                    
                    permission = self.manual_checker.check_permission(
                        model, key1, val1, key2, val2
                    )
                    
                    if permission == 'forbidden':
                        manual_problem_fields.append(key1)
                        manual_problem_fields.append(key2)
                        details.append(f"Ручной запрет: {key1}='{val1}' и {key2}='{val2}'")
                        print(f"   ❌ Ручной запрет: {key1}='{val1}' и {key2}='{val2}'")
                    elif permission == 'allowed':
                        print(f"   ✅ Ручное разрешение: {key1}='{val1}' и {key2}='{val2}'")
            
            if manual_problem_fields:
                problem_fields.extend(list(set(manual_problem_fields)))
                return False, "Обнаружены ручные запреты", problem_fields
            print(f"   ✅ Ручные правила не нарушены")
            
            # ==================== НОВАЯ ПРОВЕРКА НАДСТАВКИ ====================
            cprint(f"\n📌 ШАГ 3.5: Проверка надставки...", 'blue', bold=True)
            
            # Получаем данные о надставке
            has_head = data.get('head', False)
            head_type = data.get('head_type', '')  # 'обычная' или 'ТЕРМО'
            head_pic_out = data.get('head_pic_out', '')
            head_pic_in = data.get('head_pic_in', '')
            height_head = data.get('height_head', 0)
            
            # Проверка надставки только если она выбрана
            if has_head:
                cprint(f"   📌 Тип надставки: {head_type if head_type else 'обычная'}", 'cyan')
                cprint(f"   📌 Рисунок снаружи: {head_pic_out if head_pic_out else 'не выбран'}", 'cyan')
                cprint(f"   📌 Рисунок внутри: {head_pic_in if head_pic_in else 'не выбран'}", 'cyan')
                cprint(f"   📌 Высота надставки: {height_head} мм", 'cyan')
                
                # ============ ВСТАВЬТЕ ВАШИ УСЛОВИЯ ПРОВЕРКИ ЗДЕСЬ ============
                # Примеры условий (замените на ваши):
                
                # 1. Проверка высоты надставки
                if height_head <= 0:
                    problem_fields.append('height_head')
                    cprint(f"   ❌ Ошибка: Высота надставки должна быть больше 0", 'red')
                    return False, "Высота надставки не указана или равна 0", problem_fields
                
                if height_head < 400 and head_pic_out == 'SNG-MG':
                    problem_fields.append('height_head')
                    cprint(f"   ❌ Ошибка: Рисунок SNG-MG доступен при высоте больше или равно 400", 'red')
                    return False, "Рисунок SNG-MG доступен при высоте больше или равно 400", problem_fields
                

                
                # ============================================================
                
                cprint(f"   ✅ Проверка надставки пройдена", 'green')
            else:
                cprint(f"   ℹ️ Надставка не выбрана", 'yellow')
            
            # Шаг 4: Проверяем совместимость характеристик
            cprint(f"\n📌 ШАГ 4: Проверка совместимости характеристик...", 'blue', bold=True)
            chars_result = self.characteristics_checker.check_all(model, properties)
            if not chars_result:
                cprint(f"   ❌ Ошибка: {chars_result.message}", 'red')
                if hasattr(chars_result, 'problem_fields') and chars_result.problem_fields:
                    problem_fields.extend(chars_result.problem_fields)
                    cprint(f"   🎯 Проблемные поля: {', '.join(problem_fields)}", 'yellow')
                if hasattr(chars_result, 'details') and chars_result.details:
                    details_info = chars_result.details.get('details', [])
                    for detail in details_info:
                        cprint(f"   📝 Деталь: {detail}", 'cyan')
                return False, chars_result.message, problem_fields
            cprint(f"   ✅ Характеристики совместимы", 'green')
            
            # Шаг 5: Проверяем совместимость рисунков MDF
            cprint(f"\n📌 ШАГ 5: Проверка совместимости MDF...", 'blue', bold=True)
            out_pic = data.get('05_Лицо (рисунок)', '')
            in_pic = data.get('07_Внутр. отделка (рисунок)', '')
            has_peep = data.get('peep', False)
            peep_offset = data.get('peep_offset', False)
            
            mdf_result = self.mdf_checker.check_compatibility(
                out_pic=out_pic,
                in_pic=in_pic,
                has_peep=has_peep,
                peep_offset=peep_offset
            )
            
            if not mdf_result:
                cprint(f"   ❌ Ошибка: {mdf_result.message}", 'red')
                problem_fields.extend(['05_Лицо (рисунок)', '07_Внутр. отделка (рисунок)'])
                return False, mdf_result.message, problem_fields
            cprint(f"   ✅ MDF совместим", 'green')
            
            # Финальный успех
            cprint(f"\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Изготовление возможно.", 'green', bold=True)
            return True, "Изготовление возможно", []
            
        except Exception as e:
            cprint(f"\n❌ ОШИБКА: {e}", 'red', bold=True)
            logger.error(f"Ошибка при проверке: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Ошибка проверки: {str(e)}", problem_fields
    
    def _extract_fields_from_message(self, message: str) -> List[str]:
        """Извлекает названия полей из сообщения об ошибке"""
        fields = []
        
        field_mapping = {
            'Ширина': '01_Ширина',
            'Высота': '02_Высота',
            'Петли': '03_Петли',
            'Лицо.*цвет': '04_Лицо (цвет)',
            'Лицо.*рисунок': '05_Лицо (рисунок)',
            'Внутр.*цвет': '06_Внутр. отделка (цвет)',
            'Внутр.*рисунок': '07_Внутр. отделка (рисунок)',
            'Фурнитура': '08_Фурнитура',
            'Монтаж': '09_Монтаж',
            'Обналичка(?!.*цвет)': '10_Обналичка',
            'Обналичка.*цвет': '11_Обналичка (цвет)'
        }
        
        import re
        for pattern, field_key in field_mapping.items():
            if re.search(pattern, message, re.IGNORECASE):
                fields.append(field_key)
        
        return list(set(fields))


def is_possible_make(DB_FILE: str, mdf_db: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """Функция для обратной совместимости со старым кодом"""
    checker = DoorManufacturingChecker(DB_FILE, mdf_db)
    result, message, _ = checker.check(data)
    return result, message


def is_possible_make_detailed(DB_FILE: str, mdf_db: str, data: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    """Детальная проверка возможности изготовления"""
    checker = DoorManufacturingChecker(DB_FILE, mdf_db)
    return checker.check(data)


if __name__ == '__main__':
    doors_db = "database/doors.db"
    mdf_db = "database/mdf_pic.db"
    
    
    test_data = {
        'model': 'ULTIMATUM NEXT',
        '01_Ширина': '950',
        '02_Высота': '2000',
        '03_Петли': 'L',
        '04_Лицо (цвет)': 'ПВХ Ферро',
        '05_Лицо (рисунок)': 'Lines/ЛКП Clear',
        '06_Внутр. отделка (цвет)': 'ПВХ Ферро',
        '07_Внутр. отделка (рисунок)': 'Trixie',
        '08_Фурнитура': 'ЧКВ_БН RL_RL',
        '09_Монтаж': 'НАКЛ',
        '10_Обналичка': '-',
        '11_Обналичка (цвет)': 'Колоре гриджио',
        'peep': False,
        'peep_offset': False,
        'adv_lock': True,
        'latch': True,
        'options': []
    }
    
    cprint(f"\n{'='*60}", 'cyan', bold=True)
    cprint(f"🧪 ТЕСТИРОВАНИЕ ФУНКЦИИ is_possible_make_detailed", 'cyan', bold=True)
    cprint(f"{'='*60}", 'cyan', bold=True)
    
    try:
        result, message, problem_fields = is_possible_make_detailed(doors_db, mdf_db, test_data)
        
        print()
        if result:
            cprint(f"📊 РЕЗУЛЬТАТ: УСПЕШНО ✅", 'green', bold=True)
        else:
            cprint(f"📊 РЕЗУЛЬТАТ: НЕВОЗМОЖНО ❌", 'red', bold=True)
        
        cprint(f"📝 Сообщение: {message}", 'white')
        
        if problem_fields:
            cprint(f"⚠️ Проблемные поля: {', '.join(problem_fields)}", 'yellow', bold=True)
        else:
            cprint(f"ℹ️ Проблемные поля не определены", 'blue')
            
    except Exception as e:
        cprint(f"❌ Ошибка: {e}", 'red', bold=True)
        import traceback
        traceback.print_exc()
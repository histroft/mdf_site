"""
Калькулятор стоимости надставки (с поддержкой флага "со стеклом")
"""
import sys
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
from typing import Dict, List, Any, Tuple, Optional
from Economical.database import PriceDatabase
from Economical.normalizer import DataNormalizer
from Economical.condition_parser import ConditionParser

logger = logging.getLogger(__name__)


def format_price(price):
    if isinstance(price, (int, float)):
        return f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return str(price)


def format_price_change(price):
    if price >= 0:
        return f"+{format_price(price)}"
    return format_price(price)


class HeadPriceCalculator:
    """Калькулятор цен для надставки"""
    
    def __init__(self, db_path: str, debug: bool = False):
        self.db = PriceDatabase(db_path)
        self.normalizer = DataNormalizer()
        self.debug = debug
    
    def _has_glass_by_pic(self, pic_value: str) -> bool:
        """Определяет наличие стеклопакета по рисунку"""
        if not pic_value:
            return False
        pic_upper = pic_value.upper().strip()
        return pic_upper in ('SNG-G', 'SNG-MG')
    
    def _debug_print(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)
    
    def calculate(self, query: Dict[str, Any]) -> Tuple[float, List[str]]:
        messages = []
        
        try:
            has_head = query.get('head', False)
            if not has_head:
                return 0, messages
            
            head_type = query.get('head_type', 'обычная')
            head_height = query.get('height_head', 0)
            head_pic_out = query.get('head_pic_out', '')
            head_pic_in = query.get('head_pic_in', '')
            price_type = query.get('price_type', 'Цены ТД ТОРЭКС')
            
            # ✅ ОПРЕДЕЛЯЕМ стеклопакет ПО РИСУНКУ (а не по отдельному флагу)
            has_glass = self._has_glass_by_pic(head_pic_out) or self._has_glass_by_pic(head_pic_in)
            
            # Определяем модель надставки
            if head_type == 'ТЕРМО':
                model = 'Надставка Термо'
            else:
                model = 'Надставка'
            
            messages.append(f"\n{'='*50}")
            messages.append(f"📐 РАСЧЁТ СТОИМОСТИ НАДСТАВКИ")
            messages.append(f"{'='*50}")
            messages.append(f"Модель: {model}")
            messages.append(f"Тип: {head_type}")
            messages.append(f"Высота: {head_height} мм")
            messages.append(f"Рисунок снаружи: {head_pic_out if head_pic_out else 'не выбран'}")
            messages.append(f"Рисунок внутри: {head_pic_in if head_pic_in else 'не выбран'}")
            messages.append(f"Стеклопакет: {'Да' if has_glass else 'Нет'} (определён по рисунку)")
            messages.append(f"Тип цен: {price_type}")
            
            # Создаём запрос для надставки (включая характеристики двери)
            head_query = query.copy()
            head_query['model'] = model
            head_query['Высота надставки'] = str(head_height)
            head_query['Рисунок снаружи'] = head_pic_out
            head_query['Рисунок внутри'] = head_pic_in
            
            # Нормализуем запрос
            normalized_query = self.normalizer.normalize_query(head_query)
            
            self._debug_print(f"\n📋 Нормализованный запрос для надставки:")
            for key, value in normalized_query.items():
                if key.startswith(('04_', '06_', '01_', '02_')) or key in ['Высота надставки', 'options']:
                    self._debug_print(f"   {key}: {value}")
            
            class Context:
                def __init__(self, normalized_query):
                    self.normalized_query = normalized_query
            
            context = Context(normalized_query)
            
            # Базовая цена
            try:
                base_price, actual_price_type = self.db.get_base_price(model, price_type)
                messages.append(f"\n💰 Базовая цена: {format_price(base_price)} руб.")
            except Exception as e:
                logger.warning(f"Базовая цена для {model} не найдена: {e}")
                messages.append(f"\n⚠️ Базовая цена для {model} не найдена")
                return 0, messages
            
            total_price = base_price
            
            # Загружаем опции
            options = self.db.get_additional_options(model, price_type)
            messages.append(f"\n📋 Найдено дополнительных опций: {len(options)}")
            
            # Список выбранных опций (из запроса)
            selected_options = [opt.strip().lower() for opt in query.get('options', [])]
            
            # ✅ Добавляем опцию "Стеклопакет" если определили по рисунку
            if has_glass:
                selected_options.append('стеклопакет в надставке')
                self._debug_print(f"   Добавлена опция 'Стеклопакет' (определено по рисунку: {head_pic_out} / {head_pic_in})")
            
            self._debug_print(f"\nВыбранные опции: {selected_options}")
            
            applied_count = 0
            
            for opt_row in options:
                add_opt_id, option_id, name, is_percent_raw, price, opt_price_type = opt_row
                is_percent = bool(is_percent_raw)
                name_lower = name.strip().lower()
                
                self._debug_print(f"\n🔍 Проверка: {name}")
                
                # Получаем условия
                conditions = self.db.get_option_conditions(add_opt_id)
                
                should_apply = False
                
                if conditions:
                    # Есть условия - проверяем
                    parser = ConditionParser(context)
                    condition_met = self._check_conditions(parser, conditions, name)
                    self._debug_print(f"   Условия выполнены: {condition_met}")
                    
                    if condition_met:
                        # Для опции "Стеклопакет" - применяем ТОЛЬКО если определён по рисунку
                        if 'стеклопакет' in name_lower:
                            should_apply = has_glass
                            self._debug_print(f"   Стеклопакет, определён по рисунку: {should_apply}")
                        else:
                            # Остальные опции с условиями применяются автоматически
                            should_apply = True
                            self._debug_print(f"   Автоматическая опция - применяется")
                else:
                    # Нет условий - только если выбрана
                    should_apply = name_lower in selected_options
                    self._debug_print(f"   Нет условий, выбрана: {should_apply}")
                
                if should_apply:
                    if is_percent:
                        add_price = base_price * price / 100
                        price_desc = f"{price}% от базовой ({format_price(base_price)})"
                    else:
                        add_price = price
                        price_desc = f"фиксированная сумма ({format_price(price)})"
                    
                    if add_price == 0:
                        self._debug_print(f"   ⏭️ Пропущена (нулевая сумма)")
                        continue
                    
                    total_price += add_price
                    applied_count += 1
                    messages.append(f"\n✅ Опция '{name}' применена")
                    messages.append(f"   Тип расчета: {price_desc}")
                    messages.append(f"   Сумма: {format_price_change(add_price)}")
                    messages.append(f"   Цена после опции: {format_price(total_price)}")
            
            if applied_count == 0:
                messages.append(f"\nℹ️ Нет применённых опций")
            
            messages.append(f"\n{'-'*40}")
            messages.append(f"💵 ИТОГОВАЯ СТОИМОСТЬ НАДСТАВКИ: {format_price(total_price)} руб.")
            messages.append(f"{'-'*40}")
            
            return total_price, messages
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            import traceback
            traceback.print_exc()
            messages.append(f"\n❌ ОШИБКА: {e}")
            return 0, messages
    
    def _check_conditions(self, parser: ConditionParser, conditions: list, option_name: str = "") -> bool:
        """Проверка условий через ConditionParser"""
        if not conditions:
            return False
        
        results = []
        for cond_id, cond_or, cond_not, cond_text in conditions:
            cond_or = bool(cond_or)
            cond_not = bool(cond_not)
            properties = self.db.get_condition_properties(cond_id)
            
            if cond_text and cond_text.strip():
                condition_met = parser.parse_condition_text(cond_text)
            else:
                condition_met = parser.evaluate_condition_set(cond_id, cond_or, cond_not, properties)
            
            results.append(condition_met)
        
        # Группировка по AND/OR
        and_results, or_results = [], []
        for i, (cond_id, cond_or, cond_not, cond_text) in enumerate(conditions):
            if i < len(results):
                if cond_or:
                    or_results.append(results[i])
                else:
                    and_results.append(results[i])
        
        and_met = all(and_results) if and_results else True
        or_met = any(or_results) if or_results else True
        
        return and_met and or_met


def calculate_head_price(db_path: str, query: Dict[str, Any], debug: bool = False) -> Tuple[float, List[str]]:
    calculator = HeadPriceCalculator(db_path, debug=debug)
    return calculator.calculate(query)


if __name__ == '__main__':
    from config import Config
    
    # Тест: стеклопакет определяется по рисунку SNG-G
    test_query = {
        'head': True,
        'head_type': 'ТЕРМО',
        'height_head': 450,
        'price_type': 'Цены ТД ТОРЭКС',
        '04_Лицо (цвет)': 'ФМ Красное дерево',
        '06_Внутр. отделка (цвет)': 'ЛКП Бруно',
        '01_Ширина': '1000',
        'head_pic_out': 'SNG-G',  # ← рисунок со стеклом
        'head_pic_in': '',
        'options': []
    }
    
    db_path = Config.NEW_PATH_TO_PRICE_DB
    total_price, messages = calculate_head_price(db_path, test_query, debug=True)
    print("\n".join(messages))
    print(f"\n💰 ИТОГО: {format_price(total_price)} руб.")
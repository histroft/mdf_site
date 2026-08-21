"""
Модуль для поиска отсутствующих характеристик в исполнениях двери
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))





import sqlite3
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


class BacklightFinder:
    """Класс для поиска отсутствующих характеристик"""
    
    # Типы несовпадений
    MATCH_TYPE_FULL = 'FULL'
    MATCH_TYPE_VALUE_MISMATCH = 'VALUE_MISMATCH'
    MATCH_TYPE_MISSING_PROPERTY = 'MISSING_PROPERTY'
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: путь к базе данных
        """
        self.db_path = db_path
    
    def _get_connection(self):
        """Создание соединения с БД"""
        return sqlite3.connect(self.db_path)
    
    def _get_model_id(self, cursor, model_name: str) -> Optional[int]:
        """Получение ID модели"""
        cursor.execute(
            "SELECT model_id FROM models WHERE model_name = ?", 
            (model_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
    def _get_property_id(self, cursor, prop_name: str) -> Optional[int]:
        """Получение ID свойства"""
        cursor.execute(
            "SELECT property_id FROM properties WHERE property_name = ?", 
            (prop_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
    def _normalize_values(self, values: Any) -> List[str]:
        """
        Приводит значения к списку строк
        
        Args:
            values: значение или список значений
            
        Returns:
            List[str]: список строк
        """
        if isinstance(values, str):
            return [values.strip()]
        elif isinstance(values, (list, tuple)):
            return [str(v).strip() for v in values]
        else:
            return [str(values).strip()]
    
    def _get_variant_characteristics(self, cursor, variant_id: int) -> Dict[str, List[str]]:
        """
        Получает все характеристики варианта
        
        Args:
            cursor: курсор БД
            variant_id: ID варианта
            
        Returns:
            Dict[str, List[str]]: словарь характеристик
        """
        cursor.execute("""
            SELECT p.property_name, c.value 
            FROM characteristics c
            JOIN properties p ON c.property_id = p.property_id
            WHERE c.variant_id = ?
        """, (variant_id,))
        
        characteristics = {}
        for row in cursor.fetchall():
            prop_name = row[0]
            value = str(row[1]).strip()
            
            if prop_name not in characteristics:
                characteristics[prop_name] = []
            characteristics[prop_name].append(value)
        
        return characteristics
    
    def _get_variants(self, cursor, model_id: int) -> List[Tuple[int, str]]:
        """
        Получает все варианты для модели (исключая #777)
        
        Args:
            cursor: курсор БД
            model_id: ID модели
            
        Returns:
            List[Tuple[int, str]]: список (variant_id, unique_combination)
        """
        cursor.execute("""
            SELECT v.variant_id, v.unique_combination 
            FROM variants v 
            WHERE v.model_id = ? 
            AND v.unique_combination NOT LIKE '%#777%'
            ORDER BY v.unique_combination
        """, (model_id,))
        
        return cursor.fetchall()
    
    def _compare_variant(
        self,
        variant_characteristics: Dict[str, List[str]],
        expected_characteristics: Dict[str, List[str]]
    ) -> Tuple[int, Dict, Dict]:
        """
        Сравнивает вариант с ожидаемыми характеристиками
        
        Returns:
            Tuple[int, Dict, Dict]: (количество совпадений, отсутствующие, совпадающие)
        """
        match_score = 0
        missing = {}
        matching = {}
        
        for prop_name, expected_values in expected_characteristics.items():
            if prop_name in variant_characteristics:
                variant_values = variant_characteristics[prop_name]
                common = set(expected_values) & set(variant_values)
                
                if common:
                    match_score += 1
                    matching[prop_name] = {
                        'expected': expected_values,
                        'actual': list(common),
                        'match_type': self.MATCH_TYPE_FULL
                    }
                else:
                    missing[prop_name] = {
                        'expected': expected_values,
                        'actual': variant_values,
                        'match_type': self.MATCH_TYPE_VALUE_MISMATCH
                    }
            else:
                missing[prop_name] = {
                    'expected': expected_values,
                    'actual': [],
                    'match_type': self.MATCH_TYPE_MISSING_PROPERTY
                }
        
        return match_score, missing, matching
    
    def find_best_match(
        self,
        model_name: str,
        characteristics_dict: Dict[str, Any],
        exclude_standard: bool = True
    ) -> Dict[str, Any]:
        """
        Ищет исполнение с максимальным совпадением характеристик
        
        Args:
            model_name: название модели
            characteristics_dict: словарь характеристик
            exclude_standard: исключать ли стандартные исполнения (#777)
            
        Returns:
            Dict: результат поиска
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 1. Проверяем модель
            model_id = self._get_model_id(cursor, model_name)
            if not model_id:
                logger.warning(f"Модель не найдена: {model_name}")
                return {'error': f"Модель '{model_name}' не найдена"}
            
            # 2. Подготавливаем характеристики
            processed = {}
            for prop_name, values in characteristics_dict.items():
                prop_id = self._get_property_id(cursor, prop_name)
                if prop_id:
                    processed[prop_name] = self._normalize_values(values)
                else:
                    logger.debug(f"Свойство не найдено в БД: {prop_name}")
            
            if not processed:
                logger.warning("Ни одного свойства не найдено в БД")
                return {'error': "Ни одно из свойств не найдено в базе"}
            
            # 3. Получаем варианты
            variants = self._get_variants(cursor, model_id)
            if not variants:
                logger.warning(f"Нет вариантов для модели: {model_name}")
                return {'error': f"Для модели '{model_name}' не найдено исполнений"}
            
            # 4. Поиск лучшего варианта
            best = {
                'variant_id': None,
                'unique_combination': None,
                'match_score': -1,
                'missing': {},
                'matching': {},
                'variant_characteristics': {}
            }
            
            for variant_id, unique_combination in variants:
                variant_chars = self._get_variant_characteristics(cursor, variant_id)
                score, missing, matching = self._compare_variant(variant_chars, processed)
                
                if score > best['match_score']:
                    best.update({
                        'variant_id': variant_id,
                        'unique_combination': unique_combination,
                        'match_score': score,
                        'missing': missing,
                        'matching': matching,
                        'variant_characteristics': variant_chars
                    })
            
            # 5. Формируем результат
            total = len(processed)
            result = {
                'model': model_name,
                'variant_id': best['variant_id'],
                'unique_combination': best['unique_combination'],
                'missing_characteristics': best['missing'],
                'matching_characteristics': best['matching'],
                'match_score': best['match_score'],
                'total_characteristics': total,
                'match_percentage': round(best['match_score'] / total * 100, 2) if total > 0 else 0,
                'success': best['match_score'] > 0
            }
            
            logger.info(
                f"Найдено исполнение для {model_name}: "
                f"совпадений {best['match_score']}/{total} "
                f"({result['match_percentage']}%)"
            )
            
            return result
            
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД: {e}")
            return {'error': f"Ошибка базы данных: {str(e)}"}
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'error': f"Ошибка: {str(e)}"}
        finally:
            if conn:
                conn.close()
    
    def get_missing_characteristics(
        self,
        model_name: str,
        characteristics_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Упрощенная функция, возвращающая только отсутствующие характеристики
        
        Args:
            model_name: название модели
            characteristics_dict: словарь характеристик
            
        Returns:
            Dict: отсутствующие характеристики
        """
        result = self.find_best_match(model_name, characteristics_dict)
        
        if 'error' in result:
            return result
        
        # Преобразуем для обратной совместимости
        missing = {}
        for prop_name, info in result.get('missing_characteristics', {}).items():
            if info['match_type'] != BacklightFinder.MATCH_TYPE_FULL:
                missing[prop_name] = {
                    'expected': info['expected'],
                    'actual': info['actual'],
                    'reason': info['match_type']
                }
        
        return missing


# Для обратной совместимости
def backlight(db_file: str, model_name: str, characteristics_dict: dict) -> dict:
    """
    Функция для обратной совместимости
    
    Returns:
        dict: отсутствующие характеристики
    """
    finder = BacklightFinder(db_file)
    return finder.get_missing_characteristics(model_name, characteristics_dict)


# Тестирование
if __name__ == "__main__":
    import pprint
    import sys
    from pathlib import Path

    
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config import Config     
        
    

    db_path=Config.DATABASE
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Тестовые данные
    test_data = {
        '01_Ширина': '950',
        '02_Высота': '2100',
        '03_Петли': 'L',
        '04_Лицо (цвет)': 'ЛКП Графит',
        '05_Лицо (рисунок)': 'S60-NC1',
        '06_Внутр. отделка (цвет)': 'ПВХ Ферро',
        '07_Внутр. отделка (рисунок)': 'PK-10N',
        '08_Фурнитура': 'ХКР_МОН 3D_ALFA',
        '09_Монтаж': 'НАКЛ',
        '10_Обналичка': 'НУ-1',
        '11_Обналичка (цвет)': 'ЛКП Графит',
    }
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ФУНКЦИИ BACKLIGHT")
    print("=" * 60)
    
    # # Тест 1: Полный результат
    # print("\n1. Полный поиск лучшего совпадения:")
    # finder = BacklightFinder(db_path)
    # full_result = finder.find_best_match("SNEGIR PRO PP", test_data)
    # pprint.pprint(f" # ##  # # # # # # # full_result {full_result}")
    
    # Тест 2: Только отсутствующие (для обратной совместимости)
    model='SNEGIR PRO PP'
    characteristics=test_data
    
    
    missing = backlight(db_path, model, characteristics)
    
    s=list(missing.keys())
    print(s)


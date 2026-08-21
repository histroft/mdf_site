"""
Модуль для получения опций моделей дверей
"""

import sqlite3
import logging
from typing import List

logger = logging.getLogger(__name__)


def get_model_options(db_path: str, model_name: str) -> List[str]:
    """
    Получает список опций для указанной модели двери из базы данных SQLite.
    
    Функция выполняет поиск всех доступных опций для конкретной модели двери,
    используя связи между таблицами models, options и model_options.
    
    Args:
        db_path (str): Путь к файлу базы данных SQLite
        model_name (str): Название модели двери
        
    Returns:
        List[str]: Список названий опций для данной модели.
                  Пустой список, если модель не найдена или опции отсутствуют.
        
    Raises:
        sqlite3.Error: Если произошла ошибка при работе с базой данных
        ValueError: Если входные параметры некорректны
        
    Examples:
        >>> options = get_model_options('doors.db', 'STANDARD')
        >>> for opt in options:
        ...     print(f"- {opt}")
        - цвет
        - фурнитура
        - стекло
    """
    # Валидация входных параметров
    if not db_path or not isinstance(db_path, str):
        raise ValueError("db_path должен быть непустой строкой")
    
    if not model_name or not isinstance(model_name, str):
        raise ValueError("model_name должен быть непустой строкой")
    
    options = []
    conn = None
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем существование необходимых таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='models'")
        if not cursor.fetchone():
            logger.error("Таблица 'models' не найдена в базе данных")
            return []
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='options'")
        if not cursor.fetchone():
            logger.error("Таблица 'options' не найдена в базе данных")
            return []
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='model_options'")
        if not cursor.fetchone():
            logger.error("Таблица 'model_options' не найдена в базе данных")
            return []
        
        # Оптимизированный запрос с JOIN вместо двух отдельных запросов
        cursor.execute("""
            SELECT o.option_name 
            FROM options o
            JOIN model_options mo ON o.option_id = mo.option_id
            JOIN models m ON mo.model_id = m.model_id
            WHERE m.model_name = ?
            ORDER BY o.option_name
        """, (model_name.strip(),))
        
        # Получаем все названия опций
        options = [row[0] for row in cursor.fetchall()]
        
        if options:
            logger.info(f"Для модели '{model_name}' найдено {len(options)} опций")
        else:
            logger.info(f"Для модели '{model_name}' опции не найдены")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка базы данных при получении опций для модели '{model_name}': {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        raise
    finally:
        if conn:
            conn.close()
    
    return options


def get_model_options_with_details(db_path: str, model_name: str) -> List[dict]:
    """
    Расширенная версия функции, возвращающая детальную информацию об опциях.
    
    Args:
        db_path: путь к БД
        model_name: название модели
        
    Returns:
        List[dict]: список опций с деталями:
            - option_name: название опции
            - option_type: тип опции
            - possible_values: возможные значения
    """
    if not db_path or not model_name:
        raise ValueError("db_path и model_name обязательны")
    
    options = []
    conn = None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                o.option_name,
                o.option_type,
                o.possible_values
            FROM options o
            JOIN model_options mo ON o.option_id = mo.option_id
            JOIN models m ON mo.model_id = m.model_id
            WHERE m.model_name = ?
            ORDER BY o.option_name
        """, (model_name.strip(),))
        
        for row in cursor.fetchall():
            options.append({
                'name': row[0],
                'type': row[1],
                'possible_values': row[2].split(',') if row[2] else []
            })
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка БД: {e}")
        raise
    finally:
        if conn:
            conn.close()
    
    return options


# Для тестирования модуля

if __name__ == "__main__":
    model_name = "DELTA PRO PP"  # Замените на нужную модель
    DATABASE = 'database/doors.db'
    options = get_model_options(DATABASE, model_name)
    for option in options:
        print(f"- {option}")

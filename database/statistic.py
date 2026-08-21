"""
Модуль для работы со статистикой
"""
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class StatisticRecorder:
    """Класс для записи статистики"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Создает таблицу statistics, если её нет"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model TEXT,
                        '01_Ширина' TEXT,
                        '02_Высота' TEXT,
                        '03_Петли' TEXT,
                        '04_Лицо (цвет)' TEXT,
                        '05_Лицо (рисунок)' TEXT,
                        '06_Внутр. отделка (цвет)' TEXT,
                        '07_Внутр. отделка (рисунок)' TEXT,
                        '08_Фурнитура' TEXT,
                        '09_Монтаж' TEXT,
                        '10_Обналичка' TEXT,
                        '11_Обналичка (цвет)' TEXT,
                        record_date TIMESTAMP,
                        is_possible BOOLEAN,
                        manager TEXT,
                        peep BOOLEAN,
                        peep_offset BOOLEAN,
                        options TEXT,
                        adv_lock BOOLEAN,
                        latch BOOLEAN
                    )
                ''')
                conn.commit()
                logger.info("Таблица statistics инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации БД статистики: {e}")
    
    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка БД статистики: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def add_record(self, data: Dict[str, Any], is_possible: bool, manager: str) -> bool:
        """
        Добавляет запись в статистику
        
        Args:
            data: данные запроса
            is_possible: результат проверки
            manager: имя менеджера
            
        Returns:
            bool: True если запись успешно добавлена
        """
        try:
            # Текущая дата и время
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Форматируем опции
            options = ','.join(data.get('options', [])) if data.get('options') else ''
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO statistics (
                        model, '01_Ширина', '02_Высота', '03_Петли', 
                        '04_Лицо (цвет)', '05_Лицо (рисунок)',
                        '06_Внутр. отделка (цвет)', '07_Внутр. отделка (рисунок)', 
                        '08_Фурнитура', '09_Монтаж',
                        '10_Обналичка', '11_Обналичка (цвет)', 
                        record_date, is_possible, manager, 
                        peep, peep_offset, options, adv_lock, latch
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('model', ''),
                    data.get('01_Ширина', ''),
                    data.get('02_Высота', ''),
                    data.get('03_Петли', ''),
                    data.get('04_Лицо (цвет)', ''),
                    data.get('05_Лицо (рисунок)', ''),
                    data.get('06_Внутр. отделка (цвет)', ''),
                    data.get('07_Внутр. отделка (рисунок)', ''),
                    data.get('08_Фурнитура', ''),
                    data.get('09_Монтаж', ''),
                    data.get('10_Обналичка', ''),
                    data.get('11_Обналичка (цвет)', ''),
                    current_date,
                    is_possible,
                    manager,
                    data.get('peep', False),
                    data.get('peep_offset', False),
                    options,
                    data.get('adv_lock', False),
                    data.get('latch', False)
                ))
                
                logger.info(f"Запись статистики добавлена: менеджер={manager}, результат={is_possible}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении записи статистики: {e}")
            return False


# Глобальный экземпляр для использования в приложении
_statistic_recorder = None

def get_statistic_recorder(db_path: str) -> StatisticRecorder:
    """Получает или создает экземпляр StatisticRecorder"""
    global _statistic_recorder
    if _statistic_recorder is None:
        _statistic_recorder = StatisticRecorder(db_path)
    return _statistic_recorder

# Функция для обратной совместимости
def add_record(statistic_db: str, data: Dict[str, Any], is_possible: bool, manager: str) -> bool:
    """
    Функция для обратной совместимости
    
    Args:
        statistic_db: путь к БД статистики
        data: данные запроса
        is_possible: результат проверки
        manager: имя менеджера
        
    Returns:
        bool: True если запись успешно добавлена
    """
    recorder = get_statistic_recorder(statistic_db)
    return recorder.add_record(data, is_possible, manager)
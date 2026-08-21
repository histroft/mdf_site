"""
Работа с базой данных для экономического расчета
"""
import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Optional, Tuple, Any
from Economical.constants import PriceConstants, PriceErrors

logger = logging.getLogger(__name__)


class PriceDatabase:
    """Класс для работы с базой данных цен"""
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: путь к файлу базы данных
        """
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self):
        """Контекстный менеджер для курсора"""
        with self.get_connection() as conn:
            yield conn.cursor()
    
    def get_base_price(self, model: str, price_type: Optional[str] = None) -> Tuple[float, str]:
        """
        Получает базовую цену модели
        
        Returns:
            Tuple[float, str]: (цена, тип_цены)
        
        Raises:
            ValueError: если цена не найдена
        """
        with self.get_cursor() as cursor:
            # Пытаемся найти по указанному типу
            if price_type:
                cursor.execute(f"""
                    SELECT {PriceConstants.COL_PRICE}, {PriceConstants.COL_PRICE_TYPE}
                    FROM {PriceConstants.BASE_PRICE_TABLE}
                    WHERE {PriceConstants.COL_NOMENCLATURE} = ? 
                      AND {PriceConstants.COL_PRICE_TYPE} = ?
                    ORDER BY {PriceConstants.COL_ID} DESC LIMIT 1
                """, (model, price_type))
                
                row = cursor.fetchone()
                if row:
                    return row[0], row[1]
            
            # Ищем любой доступный тип
            cursor.execute(f"""
                SELECT {PriceConstants.COL_PRICE}, {PriceConstants.COL_PRICE_TYPE}
                FROM {PriceConstants.BASE_PRICE_TABLE}
                WHERE {PriceConstants.COL_NOMENCLATURE} = ?
                ORDER BY {PriceConstants.COL_ID} DESC LIMIT 1
            """, (model,))
            
            row = cursor.fetchone()
            if not row:
                raise ValueError(PriceErrors.NO_PRICE_FOUND.format(model=model))
            
            return row[0], row[1]
    
    def get_additional_options(self, model: str, price_type: Optional[str] = None) -> List[Tuple]:
        """
        Получает дополнительные опции для модели
        """
        
        
        with self.get_cursor() as cursor:
            query = f"""
                SELECT {PriceConstants.COL_ID}, 
                    {PriceConstants.COL_OPTION_ID},
                    {PriceConstants.COL_NAME}, 
                    {PriceConstants.COL_IS_PERCENT},
                    {PriceConstants.COL_PRICE}, 
                    {PriceConstants.COL_PRICE_TYPE}
                FROM {PriceConstants.ADDITIONAL_OPTIONS_TABLE}
                WHERE {PriceConstants.COL_NOMENCLATURE} = ?
            """
            params = [model]
            
            if price_type:
                query += f" AND {PriceConstants.COL_PRICE_TYPE} = ?"
                params.append(price_type)
            
            query += f" ORDER BY {PriceConstants.COL_ID}"
            
           
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
    
    def get_option_conditions(self, option_id: int) -> List[Tuple]:
        """
        Получает условия для опции
        
        Args:
            option_id: ID опции (из таблицы AdditionalOptions)
            
        Returns:
            List[Tuple]: список условий
        """
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                SELECT {PriceConstants.COL_CONDITION_ID},
                    {PriceConstants.COL_CONDITION_OR},
                    {PriceConstants.COL_CONDITION_NOT},
                    {PriceConstants.COL_CONDITION_TEXT}
                FROM {PriceConstants.OPTION_CONDITIONS_TABLE}
                WHERE {PriceConstants.COL_ADDITIONAL_OPTION_ID} = ?
            """, (option_id,))
            
            return cursor.fetchall()
        
    def get_condition_properties(self, condition_id: int) -> List[Tuple]:
        """
        Получает свойства условия
        """
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                SELECT {PriceConstants.COL_PROPERTY_NAME}, 
                       {PriceConstants.COL_VALUE}, 
                       {PriceConstants.COL_COMPARISON_TYPE}
                FROM {PriceConstants.CONDITION_PROPERTIES_TABLE}
                WHERE {PriceConstants.COL_CONDITION_ID} = ?
            """, (condition_id,))
            
            return cursor.fetchall()
    
    def get_available_price_types(self, model: str) -> List[str]:
        """
        Получает все доступные типы цен для модели
        """
        price_types = set()
        
        with self.get_cursor() as cursor:
            # Типы цен из базовых цен
            cursor.execute(f"""
                SELECT DISTINCT {PriceConstants.COL_PRICE_TYPE}
                FROM {PriceConstants.BASE_PRICE_TABLE}
                WHERE {PriceConstants.COL_NOMENCLATURE} = ?
            """, (model,))
            price_types.update(row[0] for row in cursor.fetchall())
            
            # Типы цен из дополнительных опций
            cursor.execute(f"""
                SELECT DISTINCT {PriceConstants.COL_PRICE_TYPE}
                FROM {PriceConstants.ADDITIONAL_OPTIONS_TABLE}
                WHERE {PriceConstants.COL_NOMENCLATURE} = ?
            """, (model,))
            price_types.update(row[0] for row in cursor.fetchall())
        
        return sorted(price_types)
    
    def get_base_price_types(self, model: str) -> List[str]:
        """
        Получает типы цен из таблицы базовых цен
        
        Args:
            model: название модели
            
        Returns:
            List[str]: список типов цен
        """
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                SELECT DISTINCT {PriceConstants.COL_PRICE_TYPE}
                FROM {PriceConstants.BASE_PRICE_TABLE}
                WHERE {PriceConstants.COL_NOMENCLATURE} = ?
                ORDER BY {PriceConstants.COL_PRICE_TYPE}
            """, (model,))
            return [row[0] for row in cursor.fetchall()]
        
    
    def get_option_price_types(self, model: str) -> List[str]:
        """
        Получает типы цен из таблицы дополнительных опций
        
        Args:
            model: название модели
            
        Returns:
            List[str]: список типов цен
        """
        with self.get_cursor() as cursor:
            cursor.execute(f"""
                SELECT DISTINCT {PriceConstants.COL_PRICE_TYPE}
                FROM {PriceConstants.ADDITIONAL_OPTIONS_TABLE}
                WHERE {PriceConstants.COL_NOMENCLATURE} = ?
                ORDER BY {PriceConstants.COL_PRICE_TYPE}
            """, (model,))
            return [row[0] for row in cursor.fetchall()]
"""
Модуль для проверки совместимости рисунков MDF
"""
import sqlite3
import logging
from typing import Tuple
from database.connection import DatabaseConnection
from validation.base import BaseChecker, CheckResult

logger = logging.getLogger(__name__)


class MDFChecker(BaseChecker):
    """Проверяет совместимость рисунков MDF"""
    
    def __init__(self, doors_db: DatabaseConnection, mdf_db_path: str):
        """
        Args:
            doors_db: подключение к основной БД
            mdf_db_path: путь к БД с рисунками MDF
        """
        super().__init__(doors_db)
        self.mdf_db_path = mdf_db_path
    
    def check_compatibility(
        self,
        out_pic: str,
        in_pic: str,
        has_peep: bool,
        peep_offset: bool
    ) -> CheckResult:
        """
        Проверяет совместимость внешнего и внутреннего рисунков по расположению глазка
        """
        # Если глазка нет - автоматически совместимо
        if not has_peep:
            return CheckResult.ok("Совместимо: дверь без глазка")
        
        conn = None
        try:
            conn = sqlite3.connect(self.mdf_db_path)
            cursor = conn.cursor()
            
            # Проверяем существование таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exterior_finishes'")
            if not cursor.fetchone():
                logger.warning("Таблица exterior_finishes не найдена, пропускаем проверку MDF")
                return CheckResult.ok("Совместимо: проверка MDF временно отключена")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interior_finishes'")
            if not cursor.fetchone():
                logger.warning("Таблица interior_finishes не найдена, пропускаем проверку MDF")
                return CheckResult.ok("Совместимо: проверка MDF временно отключена")
            
            # Определяем тип размещения
            placement = "center_placement" if not peep_offset else "side_placement"
            placement_text = "по центру" if not peep_offset else "сбоку"
            
            # Проверяем внешний рисунок
            cursor.execute(
                "SELECT center_placement, side_placement FROM exterior_finishes WHERE pattern_name = ?",
                (out_pic,)
            )
            out_row = cursor.fetchone()
            
            if not out_row:
                logger.warning(f"Внешний рисунок '{out_pic}' не найден в базе MDF")
                return CheckResult.ok(f"Совместимо: рисунок '{out_pic}' не требует проверки")
            
            # Проверяем нужное поле
            out_support = out_row[0] if not peep_offset else out_row[1]
            if out_support != "ДА":
                return CheckResult.fail(
                    f"Внешний рисунок '{out_pic}' не поддерживает глазок {placement_text}"
                )
            
            # Проверяем внутренний рисунок
            cursor.execute(
                "SELECT center_placement, side_placement FROM interior_finishes WHERE pattern_name = ?",
                (in_pic,)
            )
            in_row = cursor.fetchone()
            
            if not in_row:
                logger.warning(f"Внутренний рисунок '{in_pic}' не найден в базе MDF")
                return CheckResult.ok(f"Совместимо: рисунок '{in_pic}' не требует проверки")
            
            # Проверяем нужное поле
            in_support = in_row[0] if not peep_offset else in_row[1]
            if in_support != "ДА":
                return CheckResult.fail(
                    f"Внутренний рисунок '{in_pic}' не поддерживает глазок {placement_text}"
                )
            
            return CheckResult.ok("Совместимо")
            
        except sqlite3.Error as e:
            logger.error(f"Ошибка базы данных MDF: {e}")
            # В случае ошибки БД, не блокируем создание заказа
            return CheckResult.ok(f"Совместимо: ошибка БД ({str(e)})")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке MDF: {e}")
            return CheckResult.ok(f"Совместимо: ошибка проверки ({str(e)})")
        finally:
            if conn:
                conn.close()
"""
Базовый класс для работы с DXF документами
"""
import math

import ezdxf
import logging
from pathlib import Path
from typing import Optional, Union

from make_order.dxf_modules.inserting import insert_dxf
from make_order.dxf_modules.transforms import mirror_msp, scale_msp
from make_order.dxf_modules.primitives import draw_line_msp, draw_circle_msp
from make_order.dxf_modules.text import add_text_msp, add_multiline_text_msp


logger = logging.getLogger(__name__)


class DXFDocument:
    """
    Класс для работы с DXF документом.
    Открывает файл один раз и позволяет добавлять множество элементов.
    """
    
    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        self.doc = None
        self.msp = None
        self._load()
    
    def _load(self):
        try:
            if not self.filepath.exists():
                raise FileNotFoundError(f"Файл не найден: {self.filepath}")
            
            self.doc = ezdxf.readfile(str(self.filepath)) # type: ignore
            self.msp = self.doc.modelspace()
            logger.debug(f"DXF документ загружен: {self.filepath}")
        except Exception as e:
            logger.error(f"Ошибка загрузки DXF: {e}")
            raise
    
    def save(self, filepath: Optional[Union[str, Path]] = None):
        save_path = Path(filepath) if filepath else self.filepath
        self.doc.saveas(str(save_path)) # type: ignore
        logger.debug(f"DXF документ сохранен: {save_path}")
    
    # === ПРИМИТИВЫ ===
    
    def add_line(self, x1: float, y1: float, x2: float, y2: float,
                 color: int = 1, layer: str = "0"):
        return draw_line_msp(self.msp, x1, y1, x2, y2, color, layer)
    
    def add_circle(self, x: float, y: float, radius: float,
                   color: int = 1, layer: str = "0"):
        return draw_circle_msp(self.msp, x, y, radius, color, layer)
    
    def add_text(self, text: str, x: float, y: float, height: float = 10,
             rotation: float = 0, color: int = 1, layer: str = "0",
             style: str = "STANDARD"):
            """Добавляет текст с возможностью поворота"""
            return add_text_msp(self.msp, text, x, y, height, rotation, color,
                            layer, style)
    
    def add_multiline_text(self, lines: list, x: float, y: float, height: float = 10,
                          line_spacing: float = 1.5, **kwargs):
        return add_multiline_text_msp(self.msp, lines, x, y, height,
                                     line_spacing, **kwargs)
    
    # === ТРАНСФОРМАЦИИ ===
    
    def insert_dxf(self, source_path: Union[str, Path], offset: tuple = (0, 0, 0)):
        return insert_dxf(self.msp, str(source_path), offset)
    
    def mirror(self, axis: str = 'y'):
        return mirror_msp(self.msp, axis)
    
    def scale(self, x_scale: float, y_scale: float):
        return scale_msp(self.msp, x_scale, y_scale)
    
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    def get_bounds(self) -> tuple:
        """
        Получает границы чертежа на высоте Y=1000мм, анализируя линии.
        Возвращает: (max_x, max_y, min_x, min_y)
        - max_x, min_x: определяются на высоте Y=1000мм
        - max_y, min_y: глобальные границы по Y
        """
        import math
        
        target_y = 1000.0  # Целевая высота
        
        # Для глобальных Y границ
        global_min_y = float('inf')
        global_max_y = float('-inf')
        
        # Для X границ на целевой высоте
        min_x_at_target = float('inf')
        max_x_at_target = float('-inf')
        
        line_count = 0
        found = False
        found_at_target = False
        
        for entity in self.msp: # type: ignore
            if entity.dxftype() == 'LINE':
                line_count += 1
                start = entity.dxf.start
                end = entity.dxf.end
                
                # Обновляем глобальные Y границы
                global_min_y = min(global_min_y, start.y, end.y)
                global_max_y = max(global_max_y, start.y, end.y)
                
                y1, y2 = start.y, end.y
                
                # Проверяем, пересекает ли линия целевую высоту
                if (y1 - target_y) * (y2 - target_y) <= 0:
                    # Линия пересекает целевую высоту
                    if abs(y2 - y1) > 0.001:  # Избегаем деления на ноль
                        t = (target_y - y1) / (y2 - y1)
                        x_intersect = start.x + t * (end.x - start.x)
                        
                        min_x_at_target = min(min_x_at_target, x_intersect)
                        max_x_at_target = max(max_x_at_target, x_intersect)
                        found_at_target = True
                
                # Проверяем, лежит ли линия горизонтально на целевой высоте
                elif abs(y1 - target_y) < 1.0 and abs(y2 - target_y) < 1.0:
                    min_x_at_target = min(min_x_at_target, start.x, end.x)
                    max_x_at_target = max(max_x_at_target, start.x, end.x)
                    found_at_target = True
                
                found = True
        
        if not found:
            logger.warning("⚠️ В чертеже не найдено линий!")
            return (0, 0, 0, 0)
        return (max_x_at_target, global_max_y, min_x_at_target, global_min_y)
    
    def analyze_drawing(self) -> dict:
        """
        Анализирует все сущности в чертеже и возвращает статистику
        
        Returns:
            dict: словарь с типами сущностей и их количеством
        """
        stats = {}
        
        for entity in self.msp: # type: ignore
            etype = entity.dxftype()
            stats[etype] = stats.get(etype, 0) + 1
        
        # Сортируем для удобства
        sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
        
        logger.info("📊 Статистика сущностей в чертеже:")
        for etype, count in sorted_stats.items():
            logger.info(f"   {etype}: {count}")
        
        return sorted_stats


    def clean_drawing(self, allowed_types: set = None) -> int: # type: ignore
        """
        Удаляет все сущности, кроме разрешенных типов
        
        Args:
            allowed_types: множество разрешенных типов (например {'LINE', 'CIRCLE', 'ARC', 'LWPOLYLINE', 'TEXT', 'MTEXT'})
            
        Returns:
            int: количество удаленных сущностей
        """
        if allowed_types is None:
            # Типы по умолчанию
            allowed_types = {
                'LINE', 'CIRCLE', 'ARC', 'LWPOLYLINE', 
                'TEXT', 'MTEXT', 'ELLIPSE', 'SPLINE'
            }
        
        # Сначала покажем статистику ДО
        logger.info("🧹 Очистка чертежа от лишних сущностей")
        before_stats = self.analyze_drawing()
        
        # Собираем сущности для удаления
        to_delete = []
        for entity in self.msp: # type: ignore
            if entity.dxftype() not in allowed_types:
                to_delete.append(entity)
        
        # Удаляем
        for entity in to_delete:
            self.msp.delete_entity(entity) # type: ignore
        
        # Покажем статистику ПОСЛЕ
        after_stats = self.analyze_drawing()
        
        removed = len(to_delete)
        logger.info(f"✅ Удалено сущностей: {removed}")
        
        return removed


    def remove_duplicates(self) -> int:
        """
        Удаляет дубликаты линий (с одинаковыми координатами)
        
        Returns:
            int: количество удаленных дубликатов
        """
        from collections import defaultdict
        
        # Для линий будем хранить хеш от координат
        line_hash = defaultdict(int)
        to_delete = []
        
        for entity in self.msp: # type: ignore
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                
                # Создаем уникальный ключ для линии
                # Округляем координаты до 3 знаков
                key = (
                    round(start.x, 3), round(start.y, 3),
                    round(end.x, 3), round(end.y, 3)
                )
                
                if line_hash[key] > 0:
                    to_delete.append(entity)
                else:
                    line_hash[key] = 1
        
        for entity in to_delete:
            self.msp.delete_entity(entity) # type: ignore
        
        removed = len(to_delete)
        if removed > 0:
            logger.info(f"✅ Удалено дубликатов линий: {removed}")
        
        return removed


    def remove_zero_length_lines(self) -> int:
        """
        Удаляет линии нулевой длины (start == end)
        
        Returns:
            int: количество удаленных линий
        """
        to_delete = []
        
        for entity in self.msp: # type: ignore
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                
                # Проверяем, совпадают ли точки
                if (abs(start.x - end.x) < 0.001 and 
                    abs(start.y - end.y) < 0.001):
                    to_delete.append(entity)
        
        for entity in to_delete:
            self.msp.delete_entity(entity) # type: ignore
        
        removed = len(to_delete)
        if removed > 0:
            logger.info(f"✅ Удалено линий нулевой длины: {removed}")
        
        return removed
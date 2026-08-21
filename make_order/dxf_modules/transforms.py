"""
Модуль для трансформации DXF (масштабирование, зеркалирование)
"""
import logging
import math
import ezdxf
from ezdxf.math import Matrix44, Vec3
from typing import Tuple, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class BoundingBox:
    """Класс для расчета ограничивающего прямоугольника"""
    def __init__(self):
        self.extmin = Vec3(float('inf'), float('inf'), float('inf'))
        self.extmax = Vec3(float('-inf'), float('-inf'), float('-inf'))
    
    def extend(self, points):
        """Добавляет точки в bounding box"""
        if not isinstance(points, (list, tuple)):
            points = [points]
        
        for point in points:
            if point is None:
                continue
            try:
                v = Vec3(point)
                self.extmin = Vec3(
                    min(self.extmin.x, v.x),
                    min(self.extmin.y, v.y),
                    min(self.extmin.z, v.z)
                )
                self.extmax = Vec3(
                    max(self.extmax.x, v.x),
                    max(self.extmax.y, v.y),
                    max(self.extmax.z, v.z)
                )
            except:
                pass


def copy_entity_attributes(source, target):
    """Копирование атрибутов из одной сущности в другую"""
    target.dxf.layer = source.dxf.layer
    
    if hasattr(source.dxf, 'color'):
        target.dxf.color = source.dxf.color
    if hasattr(source.dxf, 'linetype'):
        target.dxf.linetype = source.dxf.linetype
    if hasattr(source.dxf, 'lineweight'):
        target.dxf.lineweight = source.dxf.lineweight
    if hasattr(source.dxf, 'extrusion'):
        target.dxf.extrusion = source.dxf.extrusion


# ========== ФУНКЦИИ ДЛЯ ЗЕРКАЛИРОВАНИЯ ==========

def mirror_msp(msp, axis: str = 'y', keep_in_positive: bool = True):
    """
    Зеркально отражает все сущности в пространстве модели
    
    Args:
        msp: пространство модели
        axis: 'x' или 'y'
        keep_in_positive: если True, после отражения сдвигает к нулю
    """
    logger.debug(f"Зеркалирование пространства модели по оси {axis}")
    
    # Отражаем каждую сущность
    for entity in msp:
        try:
            if axis.lower() == 'y':
                # Инвертируем X координаты
                if entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    entity.dxf.center = (-center.x, center.y, center.z)

                elif entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    entity.dxf.start = (-start.x, start.y, start.z)
                    entity.dxf.end = (-end.x, end.y, end.z)

                elif entity.dxftype() == 'ARC':
                    center = entity.dxf.center
                    entity.dxf.center = (-center.x, center.y, center.z)
                    
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    
                    # Корректируем углы
                    entity.dxf.start_angle = 180 - end_angle
                    entity.dxf.end_angle = 180 - start_angle

                elif entity.dxftype() == 'ELLIPSE':
                    center = entity.dxf.center
                    entity.dxf.center = (-center.x, center.y, center.z)
                    
                    major = entity.dxf.major_axis
                    entity.dxf.major_axis = (-major.x, major.y, major.z)

                elif entity.dxftype() == 'LWPOLYLINE':
                    points = []
                    for point in entity.get_points():
                        x, y = -point[0], point[1]
                        if len(point) > 4:
                            points.append((x, y, point[2], point[3], point[4]))
                        elif len(point) > 2:
                            points.append((x, y, point[2]))
                        else:
                            points.append((x, y))
                    entity.set_points(points)

                elif entity.dxftype() in ['TEXT', 'MTEXT', 'INSERT']:
                    if hasattr(entity.dxf, 'insert'):
                        insert = entity.dxf.insert
                        entity.dxf.insert = (-insert.x, insert.y, insert.z)
                        
                        # Для текста корректируем угол поворота
                        if entity.dxftype() == 'TEXT':
                            rotation = entity.dxf.get('rotation', 0)
                            entity.dxf.rotation = 180 - rotation
                            
            elif axis.lower() == 'x':
                # Инвертируем Y координаты
                if entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    entity.dxf.center = (center.x, -center.y, center.z)

                elif entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    entity.dxf.start = (start.x, -start.y, start.z)
                    entity.dxf.end = (end.x, -end.y, end.z)

                elif entity.dxftype() == 'ARC':
                    center = entity.dxf.center
                    entity.dxf.center = (center.x, -center.y, center.z)
                    
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    
                    # Корректируем углы
                    entity.dxf.start_angle = 360 - end_angle
                    entity.dxf.end_angle = 360 - start_angle

                elif entity.dxftype() == 'ELLIPSE':
                    center = entity.dxf.center
                    entity.dxf.center = (center.x, -center.y, center.z)
                    
                    major = entity.dxf.major_axis
                    entity.dxf.major_axis = (major.x, -major.y, major.z)

                elif entity.dxftype() == 'LWPOLYLINE':
                    points = []
                    for point in entity.get_points():
                        x, y = point[0], -point[1]
                        if len(point) > 4:
                            points.append((x, y, point[2], point[3], point[4]))
                        elif len(point) > 2:
                            points.append((x, y, point[2]))
                        else:
                            points.append((x, y))
                    entity.set_points(points)

                elif entity.dxftype() in ['TEXT', 'MTEXT', 'INSERT']:
                    if hasattr(entity.dxf, 'insert'):
                        insert = entity.dxf.insert
                        entity.dxf.insert = (insert.x, -insert.y, insert.z)
                        
                        # Для текста корректируем угол поворота
                        if entity.dxftype() == 'TEXT':
                            rotation = entity.dxf.get('rotation', 0)
                            entity.dxf.rotation = 360 - rotation
                            
        except Exception as e:
            logger.warning(f"Ошибка при отражении {entity.dxftype()}: {e}")
    
    # Если нужно сдвинуть к нулю
    if keep_in_positive:
        shift_drawing_to_zero_in_msp(msp)
    
    logger.debug("Зеркалирование завершено")


def mirror_dxf(input_file, output_file, axis='y', shift_to_zero=True):
    """
    Зеркально отражает DXF файл и при необходимости сдвигает к нулю
    
    Args:
        input_file: исходный файл
        output_file: выходной файл
        axis: 'x' или 'y'
        shift_to_zero: если True, после отражения сдвигает чертеж чтобы min точка была в 0
    """
    logger.info(f"Зеркалирование файла {input_file} по оси {axis}")
    
    doc = ezdxf.readfile(input_file) # type: ignore
    msp = doc.modelspace()
    
    # Используем mirror_msp для отражения
    mirror_msp(msp, axis, keep_in_positive=False)
    
    # Если нужно сдвинуть к нулю
    if shift_to_zero:
        shift_drawing_to_zero_in_doc(doc)
    
    # Сохраняем
    doc.saveas(output_file)
    logger.info(f"Файл сохранен: {output_file}")


def shift_drawing_to_zero_in_msp(msp):
    """
    Сдвигает чертеж в пространстве модели так, чтобы минимальная точка была в (0,0)
    """
    # Рассчитываем bounding box
    bbox = BoundingBox()
    
    for entity in msp:
        try:
            if entity.dxftype() == 'LINE':
                bbox.extend([entity.dxf.start, entity.dxf.end])
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                bbox.extend([
                    (center.x - radius, center.y - radius),
                    (center.x + radius, center.y + radius)
                ])
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                bbox.extend([
                    (center.x - radius, center.y - radius),
                    (center.x + radius, center.y + radius)
                ])
            elif entity.dxftype() == 'ELLIPSE':
                center = entity.dxf.center
                major = entity.dxf.major_axis
                ratio = entity.dxf.ratio
                minor = Vec3(major) * ratio
                bbox.extend([
                    center - major - minor,
                    center + major + minor
                ])
            elif entity.dxftype() == 'LWPOLYLINE':
                for point in entity.get_points():
                    bbox.extend([(point[0], point[1])])
            elif entity.dxftype() in ['TEXT', 'MTEXT', 'INSERT']:
                if hasattr(entity.dxf, 'insert'):
                    bbox.extend([entity.dxf.insert])
        except Exception as e:
            logger.warning(f"Ошибка при расчете bbox для {entity.dxftype()}: {e}")
    
    # Вычисляем смещение
    min_point = bbox.extmin
    offset_x = -min_point.x
    offset_y = -min_point.y
    
    if abs(offset_x) > 0.001 or abs(offset_y) > 0.001:
        logger.debug(f"   Смещение: X={offset_x:.1f}, Y={offset_y:.1f}")
        translate_matrix = Matrix44.translate(offset_x, offset_y, 0)
        
        for entity in msp:
            try:
                entity.transform(translate_matrix)
            except Exception as e:
                logger.warning(f"Ошибка при сдвиге {entity.dxftype()}: {e}")


def shift_drawing_to_zero_in_doc(doc):
    """
    Сдвигает чертеж в документе так, чтобы минимальная точка была в (0,0)
    """
    shift_drawing_to_zero_in_msp(doc.modelspace())


# ========== ФУНКЦИИ ДЛЯ МАСШТАБИРОВАНИЯ ==========

def scale_msp(msp, x_scale: float, y_scale: float):
    """
    Масштабирует все сущности в пространстве модели
    
    Args:
        msp: пространство модели
        x_scale: масштаб по X
        y_scale: масштаб по Y
    """
    entities = list(msp)
    
    for entity in entities:
        try:
            if entity.dxftype() == "LINE":
                start_x, start_y, start_z = entity.dxf.start
                end_x, end_y, end_z = entity.dxf.end
                entity.dxf.start = (start_x * x_scale, start_y * y_scale, start_z)
                entity.dxf.end = (end_x * x_scale, end_y * y_scale, end_z)

            elif entity.dxftype() == "CIRCLE":
                center_x, center_y, center_z = entity.dxf.center
                radius = entity.dxf.radius
                entity.dxf.center = (center_x * x_scale, center_y * y_scale, center_z)
                # При разных масштабах окружность превращается в эллипс
                if abs(x_scale - y_scale) > 1e-10:
                    # Преобразуем в эллипс
                    doc = entity.doc
                    new_msp = doc.modelspace()
                    color = entity.dxf.get('color', 7)
                    layer = entity.dxf.get('layer', '0')
                    
                    # Создаем эллипс
                    ellipse = new_msp.add_ellipse(
                        center=(center_x * x_scale, center_y * y_scale, center_z),
                        major_axis=(radius * abs(x_scale), 0, 0),
                        ratio=abs(y_scale / x_scale) if x_scale != 0 else 1,
                        dxfattribs={'color': color, 'layer': layer}
                    )
                    
                    # Удаляем исходную окружность
                    msp.delete_entity(entity)
                else:
                    # Равномерное масштабирование
                    entity.dxf.radius = radius * x_scale

            elif entity.dxftype() == "ARC":
                center_x, center_y, center_z = entity.dxf.center
                radius = entity.dxf.radius
                entity.dxf.center = (center_x * x_scale, center_y * y_scale, center_z)
                # При разных масштабах используем средний масштаб для радиуса
                avg_scale = (abs(x_scale) + abs(y_scale)) / 2
                entity.dxf.radius = radius * avg_scale

            elif entity.dxftype() == "LWPOLYLINE":
                points = []
                for point in entity.get_points():
                    x, y = point[0], point[1]
                    new_x = x * x_scale
                    new_y = y * y_scale
                    if len(point) > 4:
                        points.append((new_x, new_y, point[2], point[3], point[4]))
                    elif len(point) > 2:
                        points.append((new_x, new_y, point[2]))
                    else:
                        points.append((new_x, new_y))
                entity.set_points(points)

            elif entity.dxftype() == "INSERT":
                insert_x, insert_y, insert_z = entity.dxf.insert
                entity.dxf.insert = (insert_x * x_scale, insert_y * y_scale, insert_z)

            elif entity.dxftype() == "TEXT":
                if hasattr(entity.dxf, 'insert'):
                    insert_x, insert_y, insert_z = entity.dxf.insert
                    entity.dxf.insert = (insert_x * x_scale, insert_y * y_scale, insert_z)
                if hasattr(entity.dxf, 'height'):
                    avg_scale = (abs(x_scale) + abs(y_scale)) / 2
                    entity.dxf.height *= avg_scale
                    
            elif entity.dxftype() == "MTEXT":
                if hasattr(entity.dxf, 'insert'):
                    insert_x, insert_y, insert_z = entity.dxf.insert
                    entity.dxf.insert = (insert_x * x_scale, insert_y * y_scale, insert_z)
                if hasattr(entity.dxf, 'char_height'):
                    avg_scale = (abs(x_scale) + abs(y_scale)) / 2
                    entity.dxf.char_height *= avg_scale

            elif entity.dxftype() == "ELLIPSE":
                center_x, center_y, center_z = entity.dxf.center
                major_x, major_y, major_z = entity.dxf.major_axis
                
                entity.dxf.center = (center_x * x_scale, center_y * y_scale, center_z)
                entity.dxf.major_axis = (major_x * x_scale, major_y * y_scale, major_z)
                # ratio не меняется

            else:
                # Для остальных типов используем матрицу
                matrix = Matrix44.scale(x_scale, y_scale, 1.0)
                entity.transform(matrix)
                
        except Exception as e:
            logger.warning(f"Ошибка масштабирования {entity.dxftype()}: {e}")
            continue
    
    logger.debug(f"Масштабирование выполнено: x={x_scale:.3f}, y={y_scale:.3f}")


def scale_dxf_file(input_file, output_file, x_scale, y_scale):
    """
    Масштабирует DXF файл дифференциально по осям X и Y
    
    Args:
        input_file: исходный файл
        output_file: выходной файл
        x_scale: масштаб по X
        y_scale: масштаб по Y
    """
    logger.info(f"Масштабирование файла {input_file}: x={x_scale:.3f}, y={y_scale:.3f}")
    
    try:
        doc = ezdxf.readfile(input_file) # type: ignore
        msp = doc.modelspace()
        
        # Используем scale_msp для масштабирования
        scale_msp(msp, x_scale, y_scale)
        
        doc.saveas(output_file)
        logger.info(f"Файл успешно масштабирован: {output_file}")
        return output_file

    except FileNotFoundError:
        logger.error(f"Файл '{input_file}' не найден")
        return None
    except ezdxf.DXFError as e:  # type: ignore
        logger.error(f"Ошибка обработки DXF: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return None


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_bounds(msp) -> Tuple[float, float, float, float]:
    """
    Получает границы всех сущностей в пространстве модели
    
    Returns:
        (min_x, min_y, max_x, max_y)
    """
    bbox = BoundingBox()
    
    for entity in msp:
        try:
            if entity.dxftype() == 'LINE':
                bbox.extend([entity.dxf.start, entity.dxf.end])
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                bbox.extend([
                    (center.x - radius, center.y - radius),
                    (center.x + radius, center.y + radius)
                ])
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                bbox.extend([
                    (center.x - radius, center.y - radius),
                    (center.x + radius, center.y + radius)
                ])
            elif entity.dxftype() == 'LWPOLYLINE':
                for point in entity.get_points():
                    bbox.extend([(point[0], point[1])])
            elif entity.dxftype() in ['TEXT', 'MTEXT', 'INSERT']:
                if hasattr(entity.dxf, 'insert'):
                    bbox.extend([entity.dxf.insert])
        except:
            pass
    
    return (bbox.extmin.x, bbox.extmin.y, bbox.extmax.x, bbox.extmax.y)

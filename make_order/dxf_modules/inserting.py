"""
Модуль для вставки DXF файлов с правильным учетом смещения
"""
import ezdxf
import logging
import math
from pathlib import Path
from typing import Union, Tuple
from ezdxf.math import Vec3

logger = logging.getLogger(__name__)


def insert_dxf(target_msp, source_path: Union[str, Path], offset: Tuple[float, float, float] = (0, 0, 0)) -> bool:
    """
    Вставляет содержимое DXF файла в пространство модели с учетом смещения
    
    Args:
        target_msp: целевое пространство модели
        source_path: путь к исходному DXF файлу
        offset: смещение (dx, dy, dz)
    
    Returns:
        bool: True если успешно
    """
    source_path = Path(source_path)
    
    if not source_path.exists():
        logger.error(f"Файл не найден: {source_path}")
        return False
    
    try:
        source_doc = ezdxf.readfile(str(source_path)) # type: ignore
        source_msp = source_doc.modelspace()
        
        dx, dy, dz = offset
        count = 0

        # Сначала посчитаем, сколько сущностей в исходном файле
        all_entities = list(source_msp)
        logger.info(f"   Исходный файл содержит {len(all_entities)} сущностей")
        
        for entity in all_entities:
            try:
                etype = entity.dxftype()
                new_entity = None
                
                # LINE - копируем со смещением start и end
                if etype == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    new_entity = target_msp.add_line(
                        (start[0] + dx, start[1] + dy, start[2] + dz),
                        (end[0] + dx, end[1] + dy, end[2] + dz),
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # CIRCLE - копируем со смещением center
                elif etype == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    new_entity = target_msp.add_circle(
                        (center[0] + dx, center[1] + dy, center[2] + dz),
                        radius,
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # ARC - копируем со смещением center
                elif etype == 'ARC':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    new_entity = target_msp.add_arc(
                        (center[0] + dx, center[1] + dy, center[2] + dz),
                        radius,
                        start_angle,
                        end_angle,
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # LWPOLYLINE - смещаем все точки
                elif etype == 'LWPOLYLINE':
                    points = []
                    for point in entity.get_points(): # type: ignore
                        x = point[0] + dx
                        y = point[1] + dy
                        if len(point) > 2:
                            points.append((x, y, point[2]))
                        else:
                            points.append((x, y))
                    new_entity = target_msp.add_lwpolyline(
                        points,
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # TEXT - копируем со смещением insert
                elif etype == 'TEXT':
                    insert = entity.dxf.insert
                    text = entity.dxf.text
                    height = entity.dxf.height
                    rotation = entity.dxf.get('rotation', 0)
                    new_entity = target_msp.add_text(
                        text,
                        dxfattribs={
                            'height': height,
                            'insert': (insert[0] + dx, insert[1] + dy, insert[2] + dz),
                            'rotation': rotation,
                            'color': entity.dxf.get('color', 7)
                        }
                    )
                
                # MTEXT - копируем со смещением insert
                elif etype == 'MTEXT':
                    insert = entity.dxf.insert
                    text = entity.dxf.text
                    char_height = entity.dxf.get('char_height', 2.5)
                    width = entity.dxf.get('width', 0)
                    new_entity = target_msp.add_mtext(
                        text,
                        dxfattribs={
                            'char_height': char_height,
                            'width': width,
                            'insert': (insert[0] + dx, insert[1] + dy, insert[2] + dz),
                            'color': entity.dxf.get('color', 7)
                        }
                    )
                
                # POINT - копируем со смещением location
                elif etype == 'POINT':
                    location = entity.dxf.location
                    new_entity = target_msp.add_point(
                        (location[0] + dx, location[1] + dy, location[2] + dz),
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # ELLIPSE - копируем со смещением center
                elif etype == 'ELLIPSE':
                    center = entity.dxf.center
                    major_axis = entity.dxf.major_axis
                    ratio = entity.dxf.ratio
                    new_entity = target_msp.add_ellipse(
                        (center[0] + dx, center[1] + dy, center[2] + dz),
                        major_axis,
                        ratio,
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # SPLINE - копируем со смещением control points
                elif etype == 'SPLINE':
                    points = []
                    for point in entity.control_points:  # type: ignore
                        points.append((point[0] + dx, point[1] + dy, point[2] + dz))
                    degree = entity.dxf.degree
                    new_entity = target_msp.add_spline(
                        points,
                        degree=degree,
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # INSERT (блоки) - копируем со смещением insert
                elif etype == 'INSERT':
                    insert = entity.dxf.insert
                    block_name = entity.dxf.name
                    new_entity = target_msp.add_blockref(
                        block_name,
                        (insert[0] + dx, insert[1] + dy, insert[2] + dz),
                        dxfattribs={'color': entity.dxf.get('color', 7)}
                    )
                
                # Если тип не обработан, пробуем через копирование
                else:
                    new_entity = target_msp.add_entity(entity.copy())
                    if hasattr(new_entity.dxf, 'start'):
                        start = new_entity.dxf.start
                        new_entity.dxf.start = (start[0] + dx, start[1] + dy, start[2] + dz)
                    if hasattr(new_entity.dxf, 'end'):
                        end = new_entity.dxf.end
                        new_entity.dxf.end = (end[0] + dx, end[1] + dy, end[2] + dz)
                    if hasattr(new_entity.dxf, 'center'):
                        center = new_entity.dxf.center
                        new_entity.dxf.center = (center[0] + dx, center[1] + dy, center[2] + dz)
                    if hasattr(new_entity.dxf, 'insert'):
                        insert = new_entity.dxf.insert
                        new_entity.dxf.insert = (insert[0] + dx, insert[1] + dy, insert[2] + dz)
                
                if new_entity:
                    count += 1
                
            except Exception as e:
                logger.warning(f"Не удалось скопировать сущность типа {entity.dxftype()}: {e}")
                continue
        
        logger.info(f"   ✅ Скопировано {count} из {len(all_entities)} сущностей со смещением ({dx:.1f}, {dy:.1f})")
        
        # Проверим, что добавилось
        new_entities = list(target_msp)
        logger.info(f"   📊 После вставки в целевом файле {len(new_entities)} сущностей")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка вставки: {e}")
        return False

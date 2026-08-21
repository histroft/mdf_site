def debug_cut_file(self, file_path: Path):
    """
    Детальная диагностика файла разреза
    Находит все сущности, которые находятся далеко от основного чертежа
    """
    logger.info(f"   ДЕТАЛЬНАЯ ДИАГНОСТИКА ФАЙЛА: {file_path.name}")
    
    try:
        doc = ezdxf.readfile(str(file_path))
        msp = doc.modelspace()
        
        # Сначала найдем реальные границы, исключая выбросы
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        # Собираем все сущности с их координатами
        entities_info = []
        
        for entity in msp:
            etype = entity.dxftype()
            coords = []
            
            try:
                if etype == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    coords = [(start[0], start[1]), (end[0], end[1])]
                elif etype == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    coords = [(center[0], center[1])]
                    # Добавляем крайние точки
                    coords.append((center[0] + radius, center[1]))
                    coords.append((center[0] - radius, center[1]))
                elif etype == 'ARC':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    coords = [(center[0], center[1])]
                elif etype == 'LWPOLYLINE':
                    for point in entity.get_points():
                        coords.append((point[0], point[1]))
                elif etype in ['TEXT', 'MTEXT']:
                    if hasattr(entity.dxf, 'insert'):
                        insert = entity.dxf.insert
                        coords = [(insert[0], insert[1])]
                elif etype == 'INSERT':
                    if hasattr(entity.dxf, 'insert'):
                        insert = entity.dxf.insert
                        coords = [(insert[0], insert[1])]
                
                # Обновляем границы
                for x, y in coords:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
                
                # Сохраняем информацию о сущности
                entities_info.append({
                    'type': etype,
                    'layer': entity.dxf.get('layer', '0'),
                    'coords': coords,
                    'min_x': min([c[0] for c in coords]) if coords else 0,
                    'max_x': max([c[0] for c in coords]) if coords else 0,
                    'min_y': min([c[1] for c in coords]) if coords else 0,
                    'max_y': max([c[1] for c in coords]) if coords else 0
                })
                
            except Exception as e:
                logger.debug(f"      Ошибка обработки {etype}: {e}")
                continue
        
        logger.info(f"   Общие границы: X({min_x:.1f}..{max_x:.1f}), Y({min_y:.1f}..{max_y:.1f})")
        logger.info(f"   Ширина: {max_x - min_x:.1f}, Высота: {max_y - min_y:.1f}")
        
        # Находим основной кластер сущностей
        # Предполагаем, что основные сущности находятся в диапазоне 0..500
        main_cluster_min = 0
        main_cluster_max = 500
        
        far_entities = []
        for info in entities_info:
            # Если сущность далеко от основного кластера
            if info['min_x'] < -100 or info['max_x'] > 600 or info['min_y'] < -100 or info['max_y'] > 2000:
                far_entities.append(info)
        
        if far_entities:
            logger.warning(f"   ⚠️ Найдены сущности ДАЛЕКО от основного чертежа:")
            for info in far_entities:
                logger.warning(f"      Тип: {info['type']}, слой: {info['layer']}")
                logger.warning(f"         X: {info['min_x']:.1f}..{info['max_x']:.1f}")
                logger.warning(f"         Y: {info['min_y']:.1f}..{info['max_y']:.1f}")
        else:
            logger.info(f"   ✅ Все сущности в пределах основного чертежа")
        
        return far_entities
        
    except Exception as e:
        logger.error(f"   Ошибка диагностики: {e}")
        return []
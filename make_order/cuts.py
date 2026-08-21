"""
Модуль для создания разрезов двери
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from shutil import copy

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from make_order.dxf_modules.base import DXFDocument

logger = logging.getLogger(__name__)


class CutGenerator:
    """
    Класс для создания разрезов двери
    """
    
    # Путь к базовым файлам разрезов (где хранятся шаблоны)
    TEMPLATES_DIR = Path(__file__).parent / "cuttings"
    
    # Координаты для разных типов дверей (вертикальные разрезы)
    VERT_COORDS = {
        'ULTIMATUM': {
            'l_start_x': 37.8,
            'l_start_y': 1683,
            'right_point': 238.8,  # l_start_x + 201
            'u_start_x': 238.8,
            'u_start_y': 1784,  # l_start_y + 101
            'thick': 18.3,
            'size_x': -3,
            'size_y': 1114.5,
            'panel_x_start': 390,
            'width_panel': 16.2,
            'size_y_start': 1574.3,
            'size_x_start': 41.3,
            'width_size': 28
        },
        'CYBER': {
            'l_start_x': 37.8,
            'l_start_y': 1683,
            'right_point': 238.8,
            'u_start_x': 238.8,
            'u_start_y': 1784,
            'thick': 18.3,
            'size_x': -3,
            'size_y': 1114.5,
            'panel_x_start': 246.7,
            'width_panel': 16.2,
            'size_y_start': 1574.3,
            'size_x_start': 41.3,
            'width_size': 28
        },
        'S.OMEGA': {
            'l_start_x': 37.8,
            'l_start_y': 1683,
            'right_point': 238.8,
            'u_start_x': 238.8,
            'u_start_y': 1784,
            'thick': 18.3,
            'size_x': -3,
            'size_y': 1114.5,
            'panel_x_start': 246.7,
            'width_panel': 16.2,
            'size_y_start': 1574.3,
            'size_x_start': 41.3,
            'width_size': 28
        },
        'DELTA': {
            'l_start_x': 37.8,
            'l_start_y': 1683,
            'right_point': 238.8,
            'u_start_x': 238.8,
            'u_start_y': 1784,
            'thick': 18.3,
            'size_x': -3,
            'size_y': 1114.5,
            'panel_x_start': 269.7,
            'width_panel': 16.2,
            'size_y_start': 1574.3,
            'size_x_start': 41.3,
            'width_size': 28
        },
        'SNEGIR': {
            'l_start_x': 37.8,
            'l_start_y': 1683,
            'right_point': 238.8,
            'u_start_x': 238.8,
            'u_start_y': 1784,
            'thick': 18.3,
            'size_x': -3,
            'size_y': 1114.5,
            'panel_x_start': 417.32,
            'width_panel': 21.76,
            'size_y_start': 1574.3,
            'size_x_start': 41.3,
            'width_size': 28
        }
    }
    
    # Координаты для горизонтальных разрезов
    HORIZ_COORDS = {
        'left_x': 280,
        'right_x': 868,
        'left_size_x': 338.8,
        'right_size_x': 810,
        'size_y': 0,
        'size_height': 90,
        'size_offset': 58.8
    }
    
    @classmethod
    def _get_door_type_key(cls, door_type: str) -> str:
        """Определяет ключ типа двери"""
        if 'ULTIMATUM' in door_type:
            return 'ULTIMATUM'
        elif 'CYBER' in door_type:
            return 'CYBER'
        elif 'S.OMEGA' in door_type:
            return 'S.OMEGA'
        elif 'DELTA' in door_type:
            return 'DELTA'
        elif 'SNEGIR' in door_type or 'DIAMOND' in door_type:
            return 'SNEGIR'
        return 'DELTA'  # по умолчанию
    
    @classmethod
    def vert_cut(cls, data: Dict[str, Any], output_dir: Path) -> Path:
        """
        Создает вертикальный разрез в указанной папке
        
        Args:
            data: словарь с данными заказа
            output_dir: папка для сохранения результата
            
        Returns:
            Path: путь к созданному файлу
        """
        door_type = data.get('model', '')
        height = data.get('02_Высота', 0)
        vff = data.get('vff', 0)
        zff = data.get('zff', 0)
        pff = data.get('pff', 0)
        side = data.get('03_Петли', '')
        head = data.get('head', False)
        head_height = data.get('height_head', 0)
        finish_up_size = data.get('finish_up_size', 0)
        
        # Определяем тип файла и имя выходного файла
        if vff == 85 and not head:
            base_name = f'{door_type}_vert.dxf'
            out_name = 'cut_vert.dxf'
        elif head:
            base_name = f'{door_type}_vert_HEAD.dxf'
            out_name = 'cut_vert.dxf'
        elif vff < 85:
            base_name = f'{door_type}_vert36.dxf'
            out_name = 'cut_vert36.dxf'
        else:
            base_name = f'{door_type}_vert_FF.dxf'
            out_name = 'cut_vert.dxf'
        
        # Копируем базовый файл в папку заказа
        base_file = cls.TEMPLATES_DIR / base_name
        out_file = output_dir / out_name
        
        if not base_file.exists():
            logger.error(f"Базовый файл не найден: {base_file}")
            raise FileNotFoundError(f"Файл {base_name} не найден")
        
        out_file = output_dir / out_name
        copy(str(base_file), str(out_file))
        logger.debug(f"   Вертикальный разрез скопирован: {out_file}")
        
        # Если есть надставка, дорисовываем
        if head:
            cls._add_head_to_vert_cut(out_file, door_type, head_height)
        
        # Если есть фальшфрамуга, дорисовываем
        elif vff != 85 and not head and vff > 85:
            cls._add_ff_to_vert_cut(out_file, door_type, vff, finish_up_size)
        
        return out_file
    
    @classmethod
    def _add_head_to_vert_cut(cls, dxf_file: Path, door_type: str, head_height: int):
        """Добавляет надставку на вертикальный разрез"""
        doc = DXFDocument(dxf_file)
        key = cls._get_door_type_key(door_type)
        coords = cls.VERT_COORDS.get(key, cls.VERT_COORDS['DELTA'])
        
        l_start_x = coords['l_start_x']
        l_start_y = coords['l_start_y']
        right_point = coords['right_point']
        u_start_x = coords['u_start_x']
        u_start_y = coords['u_start_y']
        thick = coords['thick']
        size_x = coords['size_x']
        size_y = coords['size_y']
        
        # Левая вертикаль
        doc.add_line(l_start_x, l_start_y, 
                    l_start_x, l_start_y + (head_height - 230))
        
        # Вправо
        doc.add_line(l_start_x, l_start_y + (head_height - 230),
                    right_point, l_start_y + (head_height - 230))
        
        # Верхняя стартовая точка - вверх
        doc.add_line(u_start_x, u_start_y,
                    u_start_x, u_start_y + (head_height - 230))
        
        # Вправо
        doc.add_line(u_start_x, u_start_y + (head_height - 230),
                    u_start_x + thick, u_start_y + (head_height - 230))
        
        # Вниз
        doc.add_line(u_start_x + thick, u_start_y + (head_height - 230),
                    u_start_x + thick, u_start_y)
        
        # Размер
        doc.add_line(size_x, size_y,
                    size_x, l_start_y + (head_height - 230), color=1)
        doc.add_line(size_x - 5, l_start_y + (head_height - 230),
                    size_x + 33, l_start_y + (head_height - 230), color=1)
        
        doc.save()
        logger.debug(f"   Надставка добавлена на вертикальный разрез")
    
    @classmethod
    def _add_ff_to_vert_cut(cls, dxf_file: Path, door_type: str, vff: int, finish_up_size: float):
        """Добавляет фальшфрамугу на вертикальный разрез"""
        doc = DXFDocument(dxf_file)
        key = cls._get_door_type_key(door_type)
        
        logger.info(f"🏗️ 🏗️ 🏗️ 🏗️ Добавление фальшфрамуги на вертикальный разрез")
        logger.info(f"      Тип двери: '{door_type}'")
        logger.info(f"      Ключ: '{key}'")
        logger.info(f"      vff: {vff}, finish_up_size: {finish_up_size:.1f}")
        
        # Получаем координаты
        coords = cls.VERT_COORDS.get(key, cls.VERT_COORDS['DELTA'])
        
        # ДИАГНОСТИКА: выводим все используемые координаты
        logger.info(f"      Координаты из словаря для '{key}':")
        logger.info(f"         panel_x_start = {coords.get('panel_x_start', 'НЕТ')}")
        logger.info(f"         width_panel = {coords.get('width_panel', 'НЕТ')}")
        logger.info(f"         size_y_start = {coords.get('size_y_start', 'НЕТ')}")
        logger.info(f"         size_x_start = {coords.get('size_x_start', 'НЕТ')}")
        logger.info(f"         width_size = {coords.get('width_size', 'НЕТ')}")
        
        # Извлекаем значения
        size_y_start = coords.get('size_y_start', 1574.3)
        size_x_start = coords.get('size_x_start', 41.3)
        width_size = coords.get('width_size', 28)
        width_panel = coords.get('width_panel', 16.2)
        panel_x_start = coords.get('panel_x_start', 390)
        
        logger.info(f"      Фактические параметры для построения:")
        logger.info(f"         size_y_start = {size_y_start}")
        logger.info(f"         size_x_start = {size_x_start}")
        logger.info(f"         width_size = {width_size}")
        logger.info(f"         width_panel = {width_panel}")
        logger.info(f"         panel_x_start = {panel_x_start}")
        
        # Проверяем, какие линии будут рисоваться
        logger.info(f"      Будет нарисовано:")
        logger.info(f"         1. Вертикальная линия: ({size_x_start}, {size_y_start}) -> ({size_x_start}, {finish_up_size:.1f})")
        logger.info(f"         2. Горизонтальная линия: ({width_size}, {finish_up_size:.1f}) -> ({panel_x_start}, {finish_up_size:.1f})")
        logger.info(f"         3. Вертикальная линия панели: ({panel_x_start}, {size_y_start}) -> ({panel_x_start}, {finish_up_size:.1f})")
        logger.info(f"         4. Горизонтальная линия панели: ({panel_x_start}, {finish_up_size:.1f}) -> ({panel_x_start + width_panel}, {finish_up_size:.1f})")
        logger.info(f"         5. Вертикальная линия панели: ({panel_x_start + width_panel}, {finish_up_size:.1f}) -> ({panel_x_start + width_panel}, {size_y_start})")
        
        # Размер
        doc.add_line(size_x_start, size_y_start,
                    size_x_start, finish_up_size, color=1)
        doc.add_line(width_size, finish_up_size,
                    panel_x_start, finish_up_size, color=1)
        
        # Панель
        doc.add_line(panel_x_start, size_y_start,
                    panel_x_start, finish_up_size)
        doc.add_line(panel_x_start, finish_up_size,
                    panel_x_start + width_panel, finish_up_size)
        doc.add_line(panel_x_start + width_panel, finish_up_size,
                    panel_x_start + width_panel, size_y_start)
        
        doc.save()
        logger.info(f"   ✅ Фальшфрамуга добавлена на вертикальный разрез")
    
    @classmethod
    def horiz_cut(cls, data: Dict[str, Any], output_dir: Path) -> Path:
        
        """
        Создает горизонтальный разрез в указанной папке
        """
        door_type = data.get('model', '')
        width = data.get('01_Ширина', 0)
        vff = data.get('vff', 0)
        zff = data.get('zff', 0)
        pff = data.get('pff', 0)
        side = data.get('03_Петли', '')
        
        is_right = 'R' in side
        
        # Определяем тип файла
        if zff == 85 and pff == 85:
            base_name = f'{door_type}_horiz.dxf'
            out_name = 'cut_horiz.dxf'
        elif zff < 85 and pff < 85:
            base_name = f'{door_type}_horiz3636.dxf'
            out_name = 'cut_horiz3636.dxf'
        elif pff < 85:
            if is_right:
                base_name = f'{door_type}_horiz36R.dxf'
                out_name = 'cut_horiz36R.dxf'
            else:
                base_name = f'{door_type}_horiz36L.dxf'
                out_name = 'cut_horiz36L.dxf'
        elif zff < 85:
            if is_right:
                base_name = f'{door_type}_horiz36L.dxf'
                out_name = 'cut_horiz36L.dxf'
            else:
                base_name = f'{door_type}_horiz36R.dxf'
                out_name = 'cut_horiz36R.dxf'
        else:
            base_name = f'{door_type}_horiz_FF.dxf'
            out_name = 'cut_horiz.dxf'
        
        # Копируем базовый файл
        base_file = cls.TEMPLATES_DIR / base_name
        out_file = output_dir / out_name
        
        if not base_file.exists():
            logger.error(f"Базовый файл не найден: {base_file}")
            raise FileNotFoundError(f"Файл {base_name} не найден")
        
        copy(str(base_file), str(out_file))
        logger.debug(f"   Горизонтальный разрез скопирован: {out_file}")
        
        # Если есть фальшфрамуга, дорисовываем
        if not (zff == 85 and pff == 85) and not (zff < 85 or pff < 85):
            # Отзеркаливание происходит внутри _add_ff_to_horiz_cut
            cls._add_ff_to_horiz_cut(out_file, zff, pff, is_right)
        
        # НЕ ДОБАВЛЯТЬ ДОПОЛНИТЕЛЬНОЕ ОТЗЕРКАЛИВАНИЕ ЗДЕСЬ!
        # Отзеркаливание уже выполнено в _add_ff_to_horiz_cut
        
        return out_file
    
    @classmethod
    def _add_ff_to_horiz_cut(cls, dxf_file: Path, zff: int, pff: int, is_right: bool):
        """Добавляет фальшфрамугу на горизонтальный разрез"""
        doc = DXFDocument(dxf_file)
        coords = cls.HORIZ_COORDS
        
        left_x = coords['left_x']
        right_x = coords['right_x']
        size_height = coords['size_height']
        size_offset = coords['size_offset']
        
        if is_right:
            # Для правой двери: zff слева, pff справа
            cls._draw_horizontal_ff_side(doc, left_x, zff, size_height, is_left=True)
            cls._draw_horizontal_ff_side(doc, right_x, pff, size_height, is_left=False)
            
            # Размеры
            cls._draw_horizontal_size(doc, coords['left_size_x'], 0, zff, size_height, is_left=True)
            cls._draw_horizontal_size(doc, coords['right_size_x'], 0, pff, size_height, is_left=False)
        else:
            # Для левой двери: pff слева, zff справа
            cls._draw_horizontal_ff_side(doc, left_x, pff, size_height, is_left=True)
            cls._draw_horizontal_ff_side(doc, right_x, zff, size_height, is_left=False)
            
            # Размеры
            cls._draw_horizontal_size(doc, coords['left_size_x'], 0, pff, size_height, is_left=True)
            cls._draw_horizontal_size(doc, coords['right_size_x'], 0, zff, size_height, is_left=False)
            
            # ===== ИСПРАВЛЕННОЕ ЗЕРКАЛИРОВАНИЕ =====
            from make_order.dxf_modules.transforms import mirror_msp
            
            logger.info(f"   🪞 Отзеркаливание горизонтального разреза для левой стороны")
            
            # Используем правильную функцию отзеркаливания
            mirror_msp(doc.msp, axis='y', keep_in_positive=True)
        
        doc.save()
        logger.debug(f"   Фальшфрамуга добавлена на горизонтальный разрез")
    
    @classmethod
    def _draw_horizontal_ff_side(cls, doc, x: float, size: int, h: float, is_left: bool):
        """Рисует одну сторону фальшфрамуги"""
        if is_left:
            doc.add_line(x, h, x - size, h)
            doc.add_line(x - size, h, x - size, h + 28)
            doc.add_line(x - size, h + 28, x, h + 28)
        else:
            doc.add_line(x, h, x + size, h)
            doc.add_line(x + size, h, x + size, h + 28)
            doc.add_line(x + size, h + 28, x, h + 28)
    
    @classmethod
    def _draw_horizontal_size(cls, doc, x: float, y: float, size: int, h: float, is_left: bool):
        """Рисует размерную линию"""
        offset = 58.8
        if is_left:
            end_x = x - size - offset
            doc.add_line(x, y, end_x, y, color=1)
            doc.add_line(end_x, y, end_x, h, color=1)
        else:
            end_x = x + size + offset
            doc.add_line(x, y, end_x, y, color=1)
            doc.add_line(end_x, y, end_x, h, color=1)


# Для обратной совместимости (старые функции, адаптированные под новый формат)
def VertCut(door_type, height, vff, zff, pff, side, head, head_height, finish_up_size) -> Path:
    """Обратная совместимость - возвращает путь к временному файлу в папке cuttings"""
    data = {
        'model': door_type,
        '02_Высота': height,
        'vff': vff,
        'zff': zff,
        'pff': pff,
        '03_Петли': side,
        'head': head,
        'height_head': head_height,
        'finish_up_size': finish_up_size
    }
    # Для обратной совместимости используем cuttings
    temp_dir = Path(__file__).parent / "cuttings"
    return CutGenerator.vert_cut(data, temp_dir)


def HorizCut(door_type, width, vff, zff, pff, side) -> Path:
    """Обратная совместимость - возвращает путь к временному файлу в папке cuttings"""
    data = {
        'model': door_type,
        '01_Ширина': width,
        'vff': vff,
        'zff': zff,
        'pff': pff,
        '03_Петли': side
    }
    temp_dir = Path(__file__).parent / "cuttings"
    return CutGenerator.horiz_cut(data, temp_dir)


# =============================================================================
# ТЕСТОВЫЙ ЗАПУСК
# =============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🧪 ТЕСТОВЫЙ ЗАПУСК CutGenerator")
    print("="*60)
    
    # Тестовая папка для сохранения
    test_dir = Path('/home/alex/NEW_NST_SERVER/TEST')
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_data = {
        'model': 'DELTA PRO MP',
        '01_Ширина': 950,
        '02_Высота': 2100,
        'vff': 85,
        'zff': 85,
        'pff': 85,
        '03_Петли': 'L',
        'head': False,
        'height_head': 0,
        'finish_up_size': 2200
    }
    
    try:
        # Создаем разрезы в тестовой папке
        vert_file = CutGenerator.vert_cut(test_data, test_dir)
        print(f"✅ Вертикальный разрез: {vert_file}")
        
        horiz_file = CutGenerator.horiz_cut(test_data, test_dir)
        print(f"✅ Горизонтальный разрез: {horiz_file}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
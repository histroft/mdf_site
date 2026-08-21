"""
Модуль для создания DXF чертежа внутренней стороны двери
"""
import logging
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"📁 Добавлен путь: {project_root}")
    

import sys


project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"📁 Добавлен путь: {project_root}")
    
    
from typing import Dict, Any, Optional, Tuple
from shutil import copy

from make_order.dxf_modules.base import DXFDocument
from make_order.dxf_modules.inserting import insert_dxf

logger = logging.getLogger(__name__)


class MakeInDXF:
    """
    Класс для создания DXF чертежа внутренней стороны двери
    """
    
    # Константы
    BASE_WIDTH = 950
    BASE_HEIGHT = 2050
    PIC_BASE_WIDTH = 820
    
    # Координаты для фурнитуры
    LOCK_X = 47.8
    LOCK_Y = 946
    ADV_LOCK_Y = 1356
    LATCH_Y = 1190
    
    # Координаты для глазка
    PEEP_Y = 1440
    PEEP_RADIUS = 10
    PEEP_OFFSET_X = 47.8
    
    # Пути к ресурсам
    PIC_DIR = "Pic"
    FURNITURE_DIR = "Furniture"
    MAIN_LOCK_DIR = "main_lock/in"
    ADV_LOCK_DIR = "adv_lock"
    LATCH_DIR = "latch"
    
    def __init__(self, data: Dict[str, Any], output_dir: Path):
        """
        Args:
            data: словарь с данными заказа
        """
        self.data = data
        self.doc: Optional[DXFDocument] = None
        self.abs_path = Path(__file__).parent
        
        self.path_to_order = output_dir
        
        self._extract_data()
        self._setup_paths()
        self._prepare_base_file()
        
        # Координаты и размеры будут установлены после построения
        self.min_x = self.max_x = self.min_y = self.max_y = 0
        self.new_width = self.new_height = 0
        
        
    
    def _extract_data(self):
        """Извлекает данные из словаря"""
        self.model = self.data.get('model', '')
        self.width = int(self.data.get('01_Ширина', 0))
        self.height = int(self.data.get('02_Высота', 0))
        self.in_pic = self.data.get('07_Внутр. отделка (рисунок)', '').replace('/', '+')
        self.peep = self.data.get('peep', False)
        self.peep_offset = self.data.get('peep_offset', False)
        self.adv_lock = self.data.get('adv_lock', False)
        self.latch = self.data.get('latch', False)
        self.furniture = self.data.get('08_Фурнитура', '')
        self.side = self.data.get('03_Петли', '')
        
        logger.debug(f"Модель: {self.model}, Размеры: {self.width}x{self.height}")
        logger.debug(f"Рисунок: {self.in_pic}, Сторона: {self.side}")
        
        
        
    
    def _setup_paths(self):
        """Настройка путей к файлам"""
        self.path_to_order.mkdir(parents=True, exist_ok=True)
        self.in_file = self.path_to_order / "door_dxf_in.dxf"
        
        # Путь к базовому файлу
        self.base_file = self.abs_path / 'DXF' / self.model / f'{self.model}_in.dxf'
        
        # Путь к рисунку
        self.pic_file = self._get_pic_file_path()
        
        # Пути к фурнитуре
        self.lock_file = self.abs_path / self.FURNITURE_DIR / self.MAIN_LOCK_DIR / f"{self.furniture}.dxf"
        self.adv_lock_file = self.abs_path / self.FURNITURE_DIR / self.ADV_LOCK_DIR / f"{self.furniture}.dxf"
        self.latch_file = self.abs_path / self.FURNITURE_DIR / self.LATCH_DIR / f"{self.furniture}.dxf"
    
    def _get_pic_file_path(self) -> Path:
        """Определяет путь к файлу рисунка"""
        pic_dir = self.abs_path / self.PIC_DIR
        
        if self.in_pic.startswith("S11"):
            return pic_dir / 'S11_in.dxf'
        if self.in_pic.startswith("S12"):
            return pic_dir / 'S12_in.dxf'
        if self.in_pic.startswith("НСТ_16_"):
            pic_name = self.in_pic.replace('НСТ_16_', '') + '_in.dxf'
            return pic_dir / pic_name
        
        union_files = ['S4', 'S11', 'S12', 'Eve', 'Rhombus', 'River', 'Slice', 'Stripe', 'S1', 'S2', 'Batista']
        for file_name in union_files:
            if file_name in self.in_pic:
                return pic_dir / f'{file_name}_in.dxf'
        
        return pic_dir / f'{self.in_pic}_in.dxf'
    
    def _prepare_base_file(self):
        """Копирует базовый файл и создает документ"""
        if not self.base_file.exists():
            error_msg = f'Базовый файл не найден: {self.base_file}'
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        copy(str(self.base_file), str(self.in_file))
        logger.debug(f"Базовый файл скопирован: {self.base_file}")
        
        self.doc = DXFDocument(self.in_file)
    
    def build(self):
        """Основной метод построения чертежа"""
        logger.info("🏗️ Начало построения внутреннего вида")
        
        # ШАГ 1: Вставка рисунка
        self._insert_picture()
        
        
        
        # ШАГ 2: Масштабирование
        self._scale()
        
        # ШАГ 3: Вставка фурнитуры
        self._insert_furniture()
        
        # ШАГ 4: Получение границ
        self._get_bounds()
        
        # ШАГ 5: Добавление глазка
        self._add_peep()
        
        # ШАГ 6: Зеркалирование для правой стороны
        self._mirror_if_needed()
        
        # ШАГ 7: Делаем всё черным
        self._make_all_black()
        
        logger.info(f"✅ Построение завершено")
    
    def _insert_picture(self):
        """Вставляет рисунок на дверь"""
        if not self.in_pic or not self.pic_file.exists():
            return
        
        offset = (self.PIC_BASE_WIDTH // 2, 0, 0)
        insert_dxf(self.doc.msp, str(self.pic_file), offset) # type: ignore
        logger.debug(f"   ✅ Рисунок вставлен")
    
    def _scale(self):
        """Масштабирует чертеж"""
        x_scale = self.width / self.BASE_WIDTH
        y_scale = self.height / self.BASE_HEIGHT
        self.doc.scale(x_scale, y_scale) # type: ignore
        logger.debug(f"   ✅ Масштабирование: x={x_scale:.3f}, y={y_scale:.3f}")
    
    def _insert_furniture(self):
        """Добавляет фурнитуру"""
        # Основной замок
        if self.lock_file.exists():
            offset = (self.LOCK_X, self.LOCK_Y, 0)
            insert_dxf(self.doc.msp, str(self.lock_file), offset)# type: ignore
            logger.debug(f"   ✅ Основной замок добавлен")
        
        # Дополнительный замок
        if self.adv_lock and self.adv_lock_file.exists():
            offset = (self.LOCK_X, self.ADV_LOCK_Y, 0)
            insert_dxf(self.doc.msp, str(self.adv_lock_file), offset)# type: ignore
            logger.debug(f"   ✅ Дополнительный замок добавлен")
        
        # Задвижка
        if self.latch and self.latch_file.exists():
            offset = (self.LOCK_X, self.LATCH_Y, 0)
            insert_dxf(self.doc.msp, str(self.latch_file), offset)# type: ignore
            logger.debug(f"   ✅ Задвижка добавлена")
    
    def _get_bounds(self):
        """Получает границы чертежа"""
        self.max_x, self.max_y, self.min_x, self.min_y = self.doc.get_bounds()# type: ignore
        self.new_width = self.max_x
        self.new_height = self.max_y
        logger.debug(f"   📐 Границы: x=[{self.min_x:.1f}, {self.max_x:.1f}], y=[{self.min_y:.1f}, {self.max_y:.1f}]")
    
    def _add_peep(self):
        """Добавляет глазок, исключая фальшфрамугу из расчета"""
        if not self.peep:
            return
        
        # Получаем границы двери без учета фальшфрамуги
        door_min_x, door_min_y, door_max_x, door_max_y = self._get_door_bounds_without_ff()
        
        # Ширина двери (без фальшфрамуги)
        door_width = door_max_x - door_min_x
        
        if not self.peep_offset:
            # Глазок по центру двери
            x = door_min_x + door_width / 2
        else:
            # Глазок со смещением от левого края двери
            x = door_min_x + self.PEEP_OFFSET_X
        
        y = self.PEEP_Y  # Y координата фиксированная
        
        logger.debug(f"   👁️ Глазок: x={x:.1f}, y={y:.1f}")
        logger.debug(f"   🚪 Дверь: X({door_min_x:.1f}..{door_max_x:.1f}), ширина={door_width:.1f}")
        
        # Добавляем глазок
        self.doc.msp.add_circle( # type: ignore
            (x, y, 0),
            self.PEEP_RADIUS,
            dxfattribs={'color': 1}
        )
        logger.debug(f"   ✅ Глазок добавлен")
    
    def _mirror_if_needed(self):
        """Зеркалирует для правой стороны"""
        if 'R' in self.side:
            from make_order.dxf_modules.transforms import mirror_msp
            
            logger.info("   🪞 Зеркалирование чертежа для правой стороны")
            
            # Используем функцию mirror_msp с сохранением в положительных координатах
            mirror_msp(self.doc.msp, axis='y', keep_in_positive=True) # type: ignore
            
            logger.debug("   ✅ Чертеж отзеркален для правой стороны")
    
    def _make_all_black(self):
        """Делает все линии черными"""
        changed = 0
        for entity in self.doc.msp: # type: ignore
            if entity.dxf.get('color', 7) != 1:
                entity.dxf.color = 1
                changed += 1
        logger.debug(f"   ⚫ Изменено цветов: {changed}")
    
    def save(self):
        """Сохраняет документ"""
        if self.doc:
            self.doc.save()
            logger.debug(f"💾 Документ сохранен: {self.in_file}")
    
    def get_document(self) -> DXFDocument:
        """Возвращает документ"""
        return self.doc # type: ignore

    def _get_door_bounds_without_ff(self):
        """
        Получает границы двери, исключая линии фальшфрамуги
        Фальшфрамуга определяется как линии, которые находятся на краю и имеют определенные характеристики
        """
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        # Сначала найдем все вертикальные линии и их X координаты
        vertical_lines_x = []
        horizontal_lines_y = []
        
        for entity in self.doc.msp: # type: ignore
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                
                # Вертикальная линия (X одинаковый)
                if abs(start.x - end.x) < 0.1:
                    x = start.x
                    vertical_lines_x.append(x)
                    # Обновляем общие границы
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, start.y, end.y)
                    max_y = max(max_y, start.y, end.y)
                
                # Горизонтальная линия (Y одинаковый)
                elif abs(start.y - end.y) < 0.1:
                    y = start.y
                    horizontal_lines_y.append(y)
                    min_x = min(min_x, start.x, end.x)
                    max_x = max(max_x, start.x, end.x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
        
        # Если есть вертикальные линии, находим две самые крайние (это и есть границы двери)
        if vertical_lines_x:
            # Сортируем X координаты вертикальных линий
            vertical_lines_x.sort()
            
            # Предполагаем, что фальшфрамуга - это самая левая и самая правая линии
            # Исключаем их, если их больше 2
            if len(vertical_lines_x) > 2:
                # Используем вторую слева и вторую справа (исключаем крайние)
                door_min_x = vertical_lines_x[1]  # вторая слева
                door_max_x = vertical_lines_x[-2]  # вторая справа
            else:
                door_min_x = vertical_lines_x[0]
                door_max_x = vertical_lines_x[-1]
            
            logger.debug(f"   🚪 Границы двери (без фальшфрамуги): X({door_min_x:.1f}..{door_max_x:.1f})")
        else:
            door_min_x = min_x
            door_max_x = max_x
        
        # Аналогично для горизонтальных линий
        if horizontal_lines_y:
            horizontal_lines_y.sort()
            if len(horizontal_lines_y) > 2:
                door_min_y = horizontal_lines_y[1]
                door_max_y = horizontal_lines_y[-2]
            else:
                door_min_y = horizontal_lines_y[0]
                door_max_y = horizontal_lines_y[-1]
        else:
            door_min_y = min_y
            door_max_y = max_y
        
        return door_min_x, door_min_y, door_max_x, door_max_y
# =============================================================================
# ТЕСТОВЫЙ ЗАПУСК
# =============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # Добавляем путь к проекту
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🧪 ТЕСТОВЫЙ ЗАПУСК MakeInDXF")
    print("="*60)
    
    # Тестовая директория
    test_dir = Path('/home/alex/NEW_NST_SERVER/TEST')
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Тестовые данные
    test_data = {
        'model': 'DELTA PRO MP',
        '09_Монтаж': 'НАКЛ',
        '01_Ширина': 1200,
        '02_Высота': 2200,
        '03_Петли': 'L',
        '07_Внутр. отделка (рисунок)': 'D6-25',
        'peep': True,
        'peep_offset': False,
        'adv_lock': True,
        'latch': True,
        '08_Фурнитура': 'ЧКВ_БН TORXL_TORXL',
        'path_to_order': str(test_dir)
    }
    
    print(f"\n📋 Тестовые данные:")
    for key, value in test_data.items():
        print(f"   {key}: {value}")
    
    try:
        # Создаем чертеж
        print(f"\n🔨 Создание чертежа...")
        drawer = MakeInDXF(test_data)
        drawer.build()
        drawer.save()
        
        # Получаем границы
        bounds = drawer.get_document().get_bounds()
        print(f"\n📊 Границы готового чертежа:")
        print(f"   x=[{bounds[2]:.1f}, {bounds[0]:.1f}]")
        print(f"   y=[{bounds[3]:.1f}, {bounds[1]:.1f}]")
        print(f"   ширина: {bounds[0] - bounds[2]:.1f}")
        print(f"   высота: {bounds[1] - bounds[3]:.1f}")
        
        print(f"\n✅ Чертеж создан: {drawer.in_file}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

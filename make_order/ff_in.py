"""
Модуль для добавления фальшфрамуги к DXF чертежу внутренней стороны двери
"""
import logging
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"📁 Добавлен путь: {project_root}")
from typing import Dict, Any, List, Optional

from make_order.dxf_modules.base import DXFDocument

logger = logging.getLogger(__name__)


class AddFFIn:
    """
    Класс для добавления фальшфрамуги к чертежу внутренней стороны двери
    """
    
    # Константы
    TRIM_STANDARD = 85
    TRIM_CUT = 36
    BASE_LINE_OFFSET = 1
    PATTERN_OFFSET = 2.5
    HIGH_FF_THRESHOLD = 700
    
    # Типы линий
    DASHED_LINE = 'CONTINUOUS'      # пунктир для внутренней стороны
    SOLID_LINE = 'CONTINUOUS'    # сплошная для надставки
    
    def __init__(self, data: Dict[str, Any], doc: DXFDocument):
        """
        Инициализация построителя фальшфрамуги для внутренней стороны
        
        Args:
            data: словарь с данными заказа
            doc: открытый DXF документ
        """
        self.data = data
        self.doc = doc
        self.msp = doc.msp
        self.finish_up_size = 0
        
        logger.info("🏗️ AddFFIn: НАЧАЛО РАБОТЫ")
        
        self._extract_data()
        self._get_bounds()
        self._calculate_trim_sizes()
        self.build()
        
        logger.info(f"✅ AddFFIn: РАБОТА ЗАВЕРШЕНА, finish_up_size={self.finish_up_size:.1f}")
    
    def _extract_data(self):
        """Извлекает данные из словаря"""
        self.model = self.data.get('model', '')
        self.width = float(self.data.get('01_Ширина', 0))
        self.height = float(self.data.get('02_Высота', 0))
        self.side = self.data.get('03_Петли', '')
        self.vff = int(self.data.get('vff', 0))
        self.zff = int(self.data.get('zff', 0))
        self.pff = int(self.data.get('pff', 0))
        self.ff_pic = self.data.get('ff_pic', '')
        self.options = self.data.get('options', [])
        self.head = self.data.get('head', False)
        self.height_head = int(self.data.get('height_head', 0))
        
        logger.debug(f"   Модель: {self.model}, Сторона: {self.side}")
        logger.debug(f"   Размеры FF: vff={self.vff}, zff={self.zff}, pff={self.pff}")
    
    def _get_bounds(self):
        """Получает границы чертежа"""
        self.max_x, self.max_y, self.min_x, self.min_y = self.doc.get_bounds()
        logger.debug(f"   📐 Границы чертежа: x=[{self.min_x:.1f}, {self.max_x:.1f}], "
                    f"y=[{self.min_y:.1f}, {self.max_y:.1f}]")
    
    def _calculate_trim_sizes(self):
        """Вычисляет размеры фальшфрамуги"""
        is_right_door = 'R' in self.side
        is_in_proem = self.data.get('09_Монтаж', '') == 'ПРОЕМ'
        
        # Верхняя часть
        if is_in_proem or 'Обналичка обрезная сверху' in self.options:
            self.up_part = self.TRIM_CUT
        else:
            self.up_part = self.vff if self.vff else self.TRIM_STANDARD
        
        # Левая часть
        if is_in_proem or 'Обналичка обрезная слева' in self.options:
            self.left_part = self.TRIM_CUT
        else:
            ff_size = self.zff if is_right_door else self.pff
            self.left_part = ff_size if ff_size else self.TRIM_STANDARD
        
        # Правая часть
        if is_in_proem or 'Обналичка обрезная справа' in self.options:
            self.right_part = self.TRIM_CUT
        else:
            ff_size = self.pff if is_right_door else self.zff
            self.right_part = ff_size if ff_size else self.TRIM_STANDARD
        
        logger.debug(f"   📐 Размеры фальшфрамуги:")
        logger.debug(f"      левая: {self.left_part} мм влево")
        logger.debug(f"      правая: {self.right_part} мм вправо")
        logger.debug(f"      верх: {self.up_part} мм вверх")
    
    def build(self):
        """Основной метод построения фальшфрамуги"""
        logger.info("   🛠️ Построение фальшфрамуги")
        if self.zff>85 or self.pff>85 or self.vff>85:
            self._draw_left_part()
            self._draw_right_part()
            self._draw_up_part()

        if self.head:
            self._draw_head()
            
        
        self.finish_up_size = self.max_y + self.up_part
        logger.debug(f"   📏 finish_up_size = {self.finish_up_size:.1f}")
    
    def _draw_left_part(self):
        """Рисует левую часть фальшфрамуги (пунктир)"""
        logger.debug(f"   --- Левая часть: от X={self.min_x:.1f} влево на {self.left_part} мм (пунктир)")
        
        # Нижняя горизонталь
        self.doc.msp.add_line( # type: ignore
            (self.min_x, self.min_y),
            (self.min_x - self.left_part, self.min_y),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
        
        # Вертикаль
        self.doc.msp.add_line( # type: ignore
            (self.min_x - self.left_part, self.min_y),
            (self.min_x - self.left_part, self.max_y + self.up_part),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
        
        # Верхняя горизонталь
        self.doc.msp.add_line( # type: ignore
            (self.min_x - self.left_part, self.max_y + self.up_part),
            (self.min_x, self.max_y + self.up_part),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
    
    def _draw_right_part(self):
        """Рисует правую часть фальшфрамуги (пунктир)"""
        logger.debug(f"   --- Правая часть: от X={self.max_x:.1f} вправо на {self.right_part} мм (пунктир)")
        
        # Нижняя горизонталь
        self.doc.msp.add_line( # type: ignore
            (self.max_x, self.min_y),
            (self.max_x + self.right_part, self.min_y),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
        
        # Вертикаль
        self.doc.msp.add_line( # type: ignore
            (self.max_x + self.right_part, self.min_y),
            (self.max_x + self.right_part, self.max_y + self.up_part),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
        
        # Верхняя горизонталь
        self.doc.msp.add_line( # type: ignore
            (self.max_x + self.right_part, self.max_y + self.up_part),
            (self.max_x, self.max_y + self.up_part),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
    
    def _draw_up_part(self):
        """Рисует верхнюю часть фальшфрамуги (пунктир) и надставку (сплошная)"""
        logger.debug(f"   --- Верхняя часть: от Y={self.max_y:.1f} вверх на {self.up_part} мм")
        
        # # Левая вертикаль (пунктир)
        # self.doc.msp.add_line( # type: ignore
        #     (self.min_x, self.max_y),
        #     (self.min_x, self.max_y + self.up_part),
        #     dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        # )
        
        # Верхняя горизонталь (пунктир)
        self.doc.msp.add_line( # type: ignore
            (self.min_x - self.left_part, self.max_y + self.up_part),
            (self.max_x + self.right_part, self.max_y + self.up_part),
            dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        )
        
        # # Правая вертикаль (пунктир)
        # self.doc.msp.add_line( # type: ignore
        #     (self.max_x, self.max_y + self.up_part),
        #     (self.max_x, self.max_y),
        #     dxfattribs={'color': 4, 'linetype': self.DASHED_LINE}
        # )
        
        # Добавление надставки (сплошные линии)
        self._draw_head()
    
    def _draw_head(self):
        """Рисует надставку, если она есть (сплошными линиями)"""
        if not self.head:
            return
        
        logger.debug(f"   --- Надставка: высота {self.height_head} (сплошные)")
        
        start_x = self.min_x
        start_y = self.max_y
        end_x = self.max_x
        end_y = start_y + self.height_head
        
        # Левая вертикаль надставки (сплошная)
        self.doc.msp.add_line( # type: ignore
            (start_x, start_y),
            (start_x, end_y),
            dxfattribs={'color': 4, 'linetype': 'CONTINUOUS'}
        )
        
        # Верхняя горизонталь надставки (сплошная)
        self.doc.msp.add_line( # type: ignore
            (start_x, end_y),
            (end_x, end_y),
            dxfattribs={'color': 4, 'linetype': 'CONTINUOUS'}
        )
        
        # Правая вертикаль надставки (сплошная)
        self.doc.msp.add_line( # type: ignore
            (end_x, end_y),
            (end_x, start_y),
            dxfattribs={'color': 4, 'linetype': 'CONTINUOUS'}
        )
    
    

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
    print("🧪 ТЕСТОВЫЙ ЗАПУСК AddFFIn")
    print("="*60)
    
    # Путь к существующему DXF файлу
    test_file = Path('/home/alex/NEW_NST_SERVER/TEST/door_dxf_in.dxf')
    
    if not test_file.exists():
        print(f"❌ Файл не найден: {test_file}")
        print("Сначала создайте файл через in_dxf.py")
        sys.exit(1)
    
    # Тестовые данные
    test_data = {
        'model': 'DELTA PRO MP',
        '09_Монтаж': 'НАКЛ',
        '01_Ширина': 1200,
        '02_Высота': 2200,
        '03_Петли': 'L',
        'vff': 85,
        'zff': 300,
        'pff': 85,
        'ff_pic': 'L1',
        'options': [],
        'head': False,
        'height_head': 0
    }
    
    try:
        # Загружаем документ
        print(f"\n📂 Загрузка файла: {test_file}")
        doc = DXFDocument(test_file)
        
        # Показываем границы ДО
        bounds_before = doc.get_bounds()
        print(f"\n📊 Границы ДО:")
        print(f"   x=[{bounds_before[2]:.1f}, {bounds_before[0]:.1f}]")
        print(f"   y=[{bounds_before[3]:.1f}, {bounds_before[1]:.1f}]")
        
        # Добавляем фальшфрамугу
        print(f"\n🔨 Добавление фальшфрамуги...")
        ff = AddFFIn(test_data, doc)
        
        # Показываем границы ПОСЛЕ
        bounds_after = doc.get_bounds()
        print(f"\n📊 Границы ПОСЛЕ:")
        print(f"   x=[{bounds_after[2]:.1f}, {bounds_after[0]:.1f}]")
        print(f"   y=[{bounds_after[3]:.1f}, {bounds_after[1]:.1f}]")
        print(f"   finish_up_size = {ff.finish_up_size:.1f}")
        
        # Сохраняем результат
        output_file = test_file.parent / "door_dxf_in_with_ff.dxf"
        doc.save(output_file)
        print(f"\n✅ Результат сохранен: {output_file}")
        
        print("\n" + "="*60)
        print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
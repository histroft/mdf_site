"""
Модуль для создания главного DXF файла с чертежом двери
Версия 2.1 - динамическое позиционирование (без print)
"""
import datetime
import logging
from pathlib import Path

import sys
import ezdxf

from make_order.database import init_database, save_order_to_db



project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Импорты модулей для создания чертежей
from make_order.out_dxf import MakeOutDXF
from make_order.in_dxf import MakeInDXF
from make_order.ff_out import AddFFOut
from make_order.ff_in import AddFFIn
from make_order.notes_out import add_annotations_out
from make_order.notes_in import add_annotations_in
from make_order.cuts import VertCut, HorizCut
from make_order.dxf_modules.text_replacer import TextReplacer
from make_order.dxf_modules.dxf_to_image import dxf_to_jpg
from make_order.dxf_modules.add_watermark import add_watermark
from make_order.dxf_modules.png_to_pdf import png_to_pdf


# Импорты для работы с DXF
from make_order.dxf_modules.inserting import insert_dxf

# ==================== ЦВЕТА ДЛЯ ТЕРМИНАЛА ====================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Иконки с цветами
    SUCCESS = f"{GREEN}✅{END}"
    ERROR = f"{RED}❌{END}"
    WARNING = f"{YELLOW}⚠️{END}"
    INFO = f"{BLUE}ℹ️{END}"
    DEBUG = f"{CYAN}🔍{END}"

def cprint(text, color='white', bold=False, end='\n'):
    """Цветной print"""
    colors = {
        'red': Colors.RED,
        'green': Colors.GREEN,
        'yellow': Colors.YELLOW,
        'blue': Colors.BLUE,
        'cyan': Colors.CYAN,
        'white': ''
    }
    bold_prefix = Colors.BOLD if bold else ''
    print(f"{bold_prefix}{colors.get(color, '')}{text}{Colors.END}", end=end)

logger = logging.getLogger(__name__)


@dataclass
class DrawingInfo:
    """Информация о чертеже"""
    name: str
    file_path: Path
    width: float = 0
    height: float = 0
    min_x: float = 0
    min_y: float = 0
    max_x: float = 0
    max_y: float = 0
    position: Tuple[float, float] = (0, 0)


class MakeDoorDXF:
    """
    Класс для создания главного DXF файла с чертежом двери
    С динамическим позиционированием чертежей
    """

    # Константы для позиционирования
    # SPACING_X = 150  # Расстояние между чертежами по горизонтали
    # SPACING_Y = 150  # Расстояние между рядами по вертикали
    # MARGIN = 0     # Отступ от края листа
    
    def __init__(self, data: Dict[str, Any], output_dir: Optional[Path] = None):
        """
        Args:
            data: словарь с данными для чертежа
        """
        self.data = data
        self.SPACING_X = -400
        self.SPACING_Y = -50
        self.MARGIN = 0

        
        self.prev_sizes = None
        
        
        now = datetime.datetime.now()
        self.contract_ID = str(now.strftime("%d%m%Y%H%M%S"))
        
        # Создаем пути
        
        if output_dir is None:
            base_orders_dir = Path(__file__).parent.parent / 'orders'  # orders_new/../orders
            base_orders_dir.mkdir(exist_ok=True)
            self.path_to_order = base_orders_dir / self.contract_ID
            init_database()
        else:
            self.path_to_order = Path(output_dir)

        self.path_to_order.mkdir(parents=True, exist_ok=True)
        
        
        # Имена файлов
        self.out_file = self.path_to_order / "door_dxf_out.dxf"
        self.in_file = self.path_to_order / "door_dxf_in.dxf"
        self.vert_cut_file = self.path_to_order / "cut_vert.dxf"
        self.horiz_cut_file = self.path_to_order / "cut_horiz.dxf"
        self.main_file = self.path_to_order / "main.dxf"    
        self.png_file = self.path_to_order / "main.png"
        self.pdf_file = self.path_to_order / "main.pdf"
        
        # Информация о чертежах
        self.drawings = {
            'out': DrawingInfo(name='Вид спереди (наружный)', file_path=self.out_file),
            'in': DrawingInfo(name='Вид изнутри (внутренний)', file_path=self.in_file),
            'vert': DrawingInfo(name='Вертикальный разрез', file_path=self.vert_cut_file),
            'horiz': DrawingInfo(name='Горизонтальный разрез', file_path=self.horiz_cut_file)
        }
        
        
        # Состояние
        self.doc = None
        self.msp = None
        
        cprint(f"📁 Директория заказа: {self.path_to_order}", 'cyan')
        logger.info(f"📁 Директория заказа: {self.path_to_order}")
    
    def save_to_database(self):
        """Сохраняет данные заказа в базу данных"""
        return save_order_to_db(
            self.data, 
            self.contract_ID, 
            str(self.path_to_order)
    )
    
    
    
    def build_out(self):
        # 1. Создаем чертеж
        out = MakeOutDXF(self.data, self.path_to_order)
        
        # 2. СТРОИМ чертеж (вставка рисунка, масштабирование, фурнитура)
        out.build()  # ← ПЕРЕНЕСТИ СЮДА!
        
        # 3. Теперь добавляем обналичку (после того как чертеж готов)
        ff = AddFFOut(self.data, out.doc)
        self.data['finish_up_size'] = ff.finish_up_size
        
        # 4. Добавляем аннотации
        add_annotations_out(self.data, out.doc)
        
        # 5. Сохраняем
        out.doc.save()
        # """Строит наружный вид двери (вид спереди)"""
        # cprint("   Создание наружного вида (вид спереди)", 'blue')
        # logger.info("   Создание наружного вида (вид спереди)")
        # out = MakeOutDXF(self.data, self.path_to_order)
        # ff = AddFFOut(self.data, out.doc) # type: ignore
        # self.data['finish_up_size'] = ff.finish_up_size
        # out.build()
        # add_annotations_out(self.data, out.doc) # type: ignore
        # out.doc.save() # type: ignore
        # cprint(f"      ✅ {self.out_file}", 'green')
        # logger.debug(f"      ✅ {self.out_file}")
    
    def build_in(self):
        """Строит внутренний вид двери (вид изнутри)"""
        cprint("   Создание внутреннего вида (вид изнутри)", 'blue')
        logger.info("   Создание внутреннего вида (вид изнутри)")
        
        inn = MakeInDXF(self.data, self.path_to_order)
        
        if (self.data.get('zff', 0) > 85 or 
            self.data.get('pff', 0) > 85 or 
            self.data.get('vff', 0) > 85 or 
            self.data.get('head', False)):
            AddFFIn(self.data, inn.doc) # type: ignore
        
        inn.build()
        add_annotations_in(self.data, inn.doc) # type: ignore
        inn.doc.save() # type: ignore
        cprint(f"      ✅ {self.in_file}", 'green')
        logger.debug(f"      ✅ {self.in_file}")
    
    def build_cuts(self):
        """Строит разрезы"""
        cprint("   Создание разрезов", 'blue')
        logger.info("   Создание разрезов")
        
        # Вертикальный разрез
        cprint("      Вертикальный разрез", 'cyan')
        logger.debug("      Вертикальный разрез")
        vert_cut = VertCut(
            self.data['model'],
            self.data['02_Высота'],
            self.data['vff'],
            self.data['zff'],
            self.data['pff'],
            self.data['03_Петли'],
            self.data['head'],
            self.data['height_head'],
            self.data.get('finish_up_size', 0)
        )
        self.vert_cut_file = Path(vert_cut)
        self.drawings['vert'].file_path = self.vert_cut_file
        cprint(f"      ✅ {self.vert_cut_file}", 'green')
        logger.debug(f"      ✅ {self.vert_cut_file}")
        
        # Горизонтальный разрез
        cprint("      Горизонтальный разрез", 'cyan')
        logger.debug("      Горизонтальный разрез")
        horiz_cut = HorizCut(
            self.data['model'],
            self.data['01_Ширина'],
            self.data['vff'],
            self.data['zff'],
            self.data['pff'],
            self.data['03_Петли']
        )
        self.horiz_cut_file = Path(horiz_cut)
        self.drawings['horiz'].file_path = self.horiz_cut_file
        cprint(f"      ✅ {self.horiz_cut_file}", 'green')
        logger.debug(f"      ✅ {self.horiz_cut_file}")
        cprint(f"📤 START CLASS: zff={self.data['zff']}, pff={self.data['pff']}", 'yellow')
        print('📤  START CLASS ', self.data['zff'],self.data['pff'], self.horiz_cut_file, self.vert_cut_file)
    
    def get_drawing_bounds(self, drawing: DrawingInfo) -> DrawingInfo:
        """
        Получает границы чертежа, учитывая только линии (LINE)
        """
        try:
            doc = ezdxf.readfile(str(drawing.file_path)) # type: ignore
            msp = doc.modelspace()
            
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            
            line_count = 0
            
            for entity in msp:
                try:
                    etype = entity.dxftype()
                    
                    # Учитываем только линии (LINE)
                    if etype == 'LINE':
                        start = entity.dxf.start
                        end = entity.dxf.end
                        
                        min_x = min(min_x, start[0], end[0])
                        min_y = min(min_y, start[1], end[1])
                        max_x = max(max_x, start[0], end[0])
                        max_y = max(max_y, start[1], end[1])
                        line_count += 1
                        
                except Exception as e:
                    logger.debug(f"         Ошибка обработки сущности: {e}")
                    continue
            
            if line_count == 0:
                cprint(f"      ⚠️ В файле {drawing.file_path.name} не найдено линий!", 'yellow')
                logger.warning(f"      ⚠️ В файле {drawing.file_path.name} не найдено линий!")
                drawing.width = 0
                drawing.height = 0
                drawing.min_x = 0
                drawing.min_y = 0
                drawing.max_x = 0
                drawing.max_y = 0
            else:
                drawing.min_x = min_x
                drawing.min_y = min_y
                drawing.max_x = max_x
                drawing.max_y = max_y
                drawing.width = max_x - min_x
                drawing.height = max_y - min_y
                
                cprint(f"      {drawing.name}:", 'cyan')
                cprint(f"         линий: {line_count}", 'white')
                cprint(f"         ширина={drawing.width:.1f}, высота={drawing.height:.1f}", 'white')
                cprint(f"         границы: X({min_x:.1f}..{max_x:.1f}), Y({min_y:.1f}..{max_y:.1f})", 'white')
                
                logger.info(f"      {drawing.name}:")
                logger.info(f"         линий: {line_count}")
                logger.info(f"         ширина={drawing.width:.1f}, высота={drawing.height:.1f}")
                logger.info(f"         границы: X({min_x:.1f}..{max_x:.1f}), Y({min_y:.1f}..{max_y:.1f})")
            
            return drawing
            
        except Exception as e:
            cprint(f"   Ошибка получения границ {drawing.file_path}: {e}", 'red')
            logger.error(f"   Ошибка получения границ {drawing.file_path}: {e}")
            return drawing
    
    
    def set_spacing(self, spacing_x=None, spacing_y=None, margin=None):
        """
        Принудительно устанавливает отступы между чертежами
        """
        if spacing_x is not None:
            self.SPACING_X = spacing_x
            cprint(f"   SPACING_X установлен в {spacing_x}", 'blue')
            logger.info(f"   SPACING_X установлен в {spacing_x}")
        if spacing_y is not None:
            self.SPACING_Y = spacing_y
            cprint(f"   SPACING_Y установлен в {spacing_y}", 'blue')
            logger.info(f"   SPACING_Y установлен в {spacing_y}")
        if margin is not None:
            self.MARGIN = margin
            cprint(f"   MARGIN установлен в {margin}", 'blue')
            logger.info(f"   MARGIN установлен в {margin}")
        
        # Принудительно конвертируем в float для расчетов
        self.SPACING_X = float(self.SPACING_X)
        self.SPACING_Y = float(self.SPACING_Y)
        self.MARGIN = float(self.MARGIN)
        
        return self
    
    def calculate_positions(self):
        """
        Динамически рассчитывает позиции для всех чертежей
        на основе их фактических размеров
        """
        cprint("   📐 ДИНАМИЧЕСКИЙ РАСЧЕТ ПОЗИЦИЙ", 'cyan', bold=True)
        logger.info("   📐 ДИНАМИЧЕСКИЙ РАСЧЕТ ПОЗИЦИЙ")
        
        cprint("   ДИАГНОСТИКА ФАЙЛОВ РАЗРЕЗОВ:", 'yellow')
        logger.info("   ДИАГНОСТИКА ФАЙЛОВ РАЗРЕЗОВ:")
        
        
        # Получаем размеры всех чертежей
        for key, drawing in self.drawings.items():
            if drawing.file_path.exists():
                self.get_drawing_bounds(drawing)
            else:
                cprint(f"      ⚠️ Файл {drawing.file_path} не найден", 'yellow')
                logger.warning(f"      ⚠️ Файл {drawing.file_path} не найден")
        
        # Получаем размеры
        out_width = self.drawings['out'].width
        out_height = self.drawings['out'].height
        vert_width = self.drawings['vert'].width
        vert_height = self.drawings['vert'].height
        in_width = self.drawings['in'].width
        in_height = self.drawings['in'].height
        horiz_width = self.drawings['horiz'].width
        horiz_height = self.drawings['horiz'].height
        
        cprint("   РАЗМЕРЫ ЧЕРТЕЖЕЙ:", 'blue', bold=True)
        logger.info("   РАЗМЕРЫ ЧЕРТЕЖЕЙ:")
        cprint(f"      OUT: ширина={out_width:.1f}, высота={out_height:.1f}", 'white')
        cprint(f"      VERT: ширина={vert_width:.1f}, высота={vert_height:.1f}", 'white')
        cprint(f"      IN: ширина={in_width:.1f}, высота={in_height:.1f}", 'white')
        cprint(f"      HORIZ: ширина={horiz_width:.1f}, высота={horiz_height:.1f}", 'white')
        logger.info(f"      OUT: ширина={out_width:.1f}, высота={out_height:.1f}")
        logger.info(f"      VERT: ширина={vert_width:.1f}, высота={vert_height:.1f}")
        logger.info(f"      IN: ширина={in_width:.1f}, высота={in_height:.1f}")
        logger.info(f"      HORIZ: ширина={horiz_width:.1f}, высота={horiz_height:.1f}")
        
        # Вычисляем отступы АВТОМАТИЧЕСКИ на основе размеров
        # Горизонтальный отступ = 10% от ширины самого широкого чертежа, но не менее 100
        max_width = max(out_width, vert_width, in_width)
        auto_spacing_x = max(100, max_width * 0.1)
        
        # Вертикальный отступ = 10% от высоты верхнего ряда, но не менее 100
        max_height = max(out_height, vert_height, in_height)
        auto_spacing_y = max(100, max_height * 0.1)
        
        cprint("   АВТОМАТИЧЕСКИЕ ОТСТУПЫ:", 'blue')
        logger.info("   АВТОМАТИЧЕСКИЕ ОТСТУПЫ:")
        cprint(f"      SPACING_X = {auto_spacing_x:.1f} (10% от {max_width:.1f})", 'cyan')
        cprint(f"      SPACING_Y = {auto_spacing_y:.1f} (10% от {max_height:.1f})", 'cyan')
        cprint(f"      MARGIN = 100", 'cyan')
        logger.info(f"      SPACING_X = {auto_spacing_x:.1f} (10% от {max_width:.1f})")
        logger.info(f"      SPACING_Y = {auto_spacing_y:.1f} (10% от {max_height:.1f})")
        logger.info(f"      MARGIN = 100")
        
        # Устанавливаем отступы
        self.SPACING_X = auto_spacing_x
        self.SPACING_Y = auto_spacing_y
        self.MARGIN = 100
        
        # Рассчитываем позиции
        current_x = self.MARGIN
        cprint(f"   Начальная X позиция: {current_x:.1f}", 'cyan')
        logger.info(f"   Начальная X позиция: {current_x:.1f}")
        
        # Верхний ряд - Y координата = MARGIN + высота нижнего чертежа + SPACING_Y
        y_top = self.MARGIN + horiz_height + self.SPACING_Y
        cprint(f"   Y верхнего ряда = {y_top:.1f}", 'cyan')
        logger.info(f"   Y верхнего ряда = {y_top:.1f}")
        
        # ВИД СПЕРЕДИ (слева)
        out_x = current_x
        out_y = y_top-58
        self.drawings['out'].position = (out_x, out_y)
        cprint(f"   OUT позиция: ({out_x:.1f}, {out_y:.1f})", 'green')
        logger.info(f"   OUT позиция: ({out_x:.1f}, {out_y:.1f})")
        current_x += out_width + self.SPACING_X
        cprint(f"      После OUT X = {current_x:.1f}", 'cyan')
        logger.info(f"      После OUT X = {current_x:.1f}")
        
        # ВЕРТИКАЛЬНЫЙ РАЗРЕЗ (по центру)
        vert_x = current_x
        vert_y = y_top
        self.drawings['vert'].position = (vert_x, vert_y)
        cprint(f"   VERT позиция: ({vert_x:.1f}, {vert_y:.1f})", 'green')
        logger.info(f"   VERT позиция: ({vert_x:.1f}, {vert_y:.1f})")
        current_x += vert_width + self.SPACING_X
        cprint(f"      После VERT X = {current_x:.1f}", 'cyan')
        logger.info(f"      После VERT X = {current_x:.1f}")
        
        # ВИД ИЗНУТРИ (справа)
        in_x = current_x
        in_y = y_top
        self.drawings['in'].position = (in_x, in_y)
        cprint(f"   IN позиция: ({in_x:.1f}, {in_y:.1f})", 'green')
        logger.info(f"   IN позиция: ({in_x:.1f}, {in_y:.1f})")
        
        # ГОРИЗОНТАЛЬНЫЙ РАЗРЕЗ (внизу под видом спереди)
        horiz_x = self.MARGIN
        horiz_y = self.MARGIN+50
        self.drawings['horiz'].position = (horiz_x, horiz_y)
        cprint(f"   HORIZ позиция: ({horiz_x:.1f}, {horiz_y:.1f})", 'green')
        logger.info(f"   HORIZ позиция: ({horiz_x:.1f}, {horiz_y:.1f})")
        
        # Проверяем расстояния между чертежами
        cprint("   ПРОВЕРКА РАССТОЯНИЙ:", 'blue', bold=True)
        logger.info("   ПРОВЕРКА РАССТОЯНИЙ:")
        
        dist_out_vert = self.drawings['vert'].position[0] - (self.drawings['out'].position[0] + out_width)
        cprint(f"      OUT -> VERT: {dist_out_vert:.1f} (должно быть {self.SPACING_X:.1f})", 'white')
        logger.info(f"      OUT -> VERT: {dist_out_vert:.1f} (должно быть {self.SPACING_X:.1f})")
        
        dist_vert_in = self.drawings['in'].position[0] - (self.drawings['vert'].position[0] + vert_width)
        cprint(f"      VERT -> IN: {dist_vert_in:.1f} (должно быть {self.SPACING_X:.1f})", 'white')
        logger.info(f"      VERT -> IN: {dist_vert_in:.1f} (должно быть {self.SPACING_X:.1f})")
        
        dist_vertical = self.drawings['out'].position[1] - (self.drawings['horiz'].position[1] + horiz_height)
        cprint(f"      По вертикали: {dist_vertical:.1f} (должно быть {self.SPACING_Y:.1f})", 'white')
        logger.info(f"      По вертикали: {dist_vertical:.1f} (должно быть {self.SPACING_Y:.1f})")
        
        # Проверяем, не наезжают ли чертежи друг на друга
        cprint("   ПРОВЕРКА НА НАЕЗДЫ:", 'blue', bold=True)
        logger.info("   ПРОВЕРКА НА НАЕЗДЫ:")
        
        # OUT и VERT
        out_right = out_x + out_width
        vert_left = vert_x
        if out_right > vert_left:
            cprint(f"      ❌ OUT наезжает на VERT: OUT.right={out_right:.1f} > VERT.left={vert_left:.1f}", 'red')
            logger.error(f"      ❌ OUT наезжает на VERT: OUT.right={out_right:.1f} > VERT.left={vert_left:.1f}")
            # Корректируем позицию VERT
            new_vert_x = out_right + self.SPACING_X
            self.drawings['vert'].position = (new_vert_x, vert_y)
            cprint(f"         Исправлено: VERT перенесен на X={new_vert_x:.1f}", 'green')
            logger.info(f"         Исправлено: VERT перенесен на X={new_vert_x:.1f}")
        else:
            cprint(f"      ✅ OUT и VERT не пересекаются: зазор {vert_left - out_right:.1f}", 'green')
            logger.info(f"      ✅ OUT и VERT не пересекаются: зазор {vert_left - out_right:.1f}")
        
        # VERT и IN
        vert_right = vert_x + vert_width
        in_left = in_x
        if vert_right > in_left:
            cprint(f"      ❌ VERT наезжает на IN: VERT.right={vert_right:.1f} > IN.left={in_left:.1f}", 'red')
            logger.error(f"      ❌ VERT наезжает на IN: VERT.right={vert_right:.1f} > IN.left={in_left:.1f}")
            # Корректируем позицию IN
            new_in_x = vert_right + self.SPACING_X
            self.drawings['in'].position = (new_in_x, in_y)
            cprint(f"         Исправлено: IN перенесен на X={new_in_x:.1f}", 'green')
            logger.info(f"         Исправлено: IN перенесен на X={new_in_x:.1f}")
        else:
            cprint(f"      ✅ VERT и IN не пересекаются: зазор {in_left - vert_right:.1f}", 'green')
            logger.info(f"      ✅ VERT и IN не пересекаются: зазор {in_left - vert_right:.1f}")
        
        # OUT и HORIZ по вертикали
        out_bottom = out_y
        horiz_top = horiz_y + horiz_height
        if out_bottom < horiz_top:
            cprint(f"      ❌ OUT наезжает на HORIZ по вертикали: OUT.bottom={out_bottom:.1f} < HORIZ.top={horiz_top:.1f}", 'red')
            logger.error(f"      ❌ OUT наезжает на HORIZ по вертикали: OUT.bottom={out_bottom:.1f} < HORIZ.top={horiz_top:.1f}")
            # Корректируем позицию OUT
            new_out_y = horiz_top + self.SPACING_Y
            self.drawings['out'].position = (out_x, new_out_y)
            self.drawings['vert'].position = (vert_x, new_out_y)
            self.drawings['in'].position = (in_x, new_out_y)
            cprint(f"         Исправлено: верхний ряд перенесен на Y={new_out_y:.1f}", 'green')
            logger.info(f"         Исправлено: верхний ряд перенесен на Y={new_out_y:.1f}")
        else:
            cprint(f"      ✅ OUT и HORIZ не пересекаются по вертикали: зазор {out_bottom - horiz_top:.1f}", 'green')
            logger.info(f"      ✅ OUT и HORIZ не пересекаются по вертикали: зазор {out_bottom - horiz_top:.1f}")
        
        # Итоговые позиции после коррекции
        cprint("   ИТОГОВЫЕ ПОЗИЦИИ ПОСЛЕ КОРРЕКЦИИ:", 'blue', bold=True)
        logger.info("   ИТОГОВЫЕ ПОЗИЦИИ ПОСЛЕ КОРРЕКЦИИ:")
        for key, drawing in self.drawings.items():
            cprint(f"      {drawing.name}: {drawing.position}", 'cyan')
            logger.info(f"      {drawing.name}: {drawing.position}")
        
    def insert_drawing(self, drawing: DrawingInfo):
        """
        Вставляет чертеж в главный файл
        """
        tx, ty = drawing.position
        cprint(f"      Вставка {drawing.name} в ({tx:.0f}, {ty:.0f})", 'blue')
        logger.info(f"      Вставка {drawing.name} в ({tx:.0f}, {ty:.0f})")
        
        try:
            # Вычисляем смещение так, чтобы левый нижний угол встал в target_pos
            offset_x = tx - drawing.min_x
            offset_y = ty - drawing.min_y
            cprint(f"         Смещение: ({offset_x:.0f}, {offset_y:.0f})", 'cyan')
            logger.debug(f"         Смещение: ({offset_x:.0f}, {offset_y:.0f})")
            
            # Вставляем со смещением
            success = insert_dxf(
                self.msp,
                str(drawing.file_path),
                (offset_x, offset_y, 0)
            )
            
            if success:
                cprint(f"         ✅ {drawing.name} вставлен", 'green')
                logger.info(f"         ✅ {drawing.name} вставлен")
            else:
                cprint(f"         ❌ Ошибка вставки {drawing.name}", 'red')
                logger.error(f"         ❌ Ошибка вставки {drawing.name}")
            
            return success
            
        except Exception as e:
            cprint(f"      Ошибка при вставке {drawing.name}: {e}", 'red')
            logger.error(f"      Ошибка при вставке {drawing.name}: {e}")
            return False
    
    def assemble_main(self):
        """
        Собирает все файлы в главный main.dxf с динамическим позиционированием
        """
        cprint("   Сборка главного файла", 'blue', bold=True)
        logger.info("   Сборка главного файла")
        
        # Проверяем существование всех файлов
        # if not self.check_files():
        #     raise FileNotFoundError("Не все файлы созданы")
        
        # Динамически рассчитываем позиции
        self.calculate_positions()
        
        # Создаем главный DXF документ
        cprint("      Создание нового документа", 'cyan')
        logger.debug("      Создание нового документа")
        self.doc = ezdxf.new(dxfversion='AC1024') # type: ignore
        self.msp = self.doc.modelspace()
        
        # Вставляем файлы
        cprint("      Вставка файлов:", 'blue')
        logger.info("      Вставка файлов:")
        
        # Горизонтальный разрез (снизу)
        self.insert_drawing(self.drawings['horiz'])
        
        # Вид спереди (слева вверху)
        self.insert_drawing(self.drawings['out'])
        
        # Вертикальный разрез (по центру вверху)
        self.insert_drawing(self.drawings['vert'])
        
        # Вид изнутри (справа вверху)
        self.insert_drawing(self.drawings['in'])
        
        
        
        
        
        # Добавляет нижнюю подпись
        self.add_bottom_text()
        
        # Добавляет подпись слева
        self.add_left_text()
        
        # Сохраняем главный файл
        self.doc.saveas(str(self.main_file))
        cprint(f"   ✅ Главный файл создан: {self.main_file}", 'green')
        logger.info(f"   ✅ Главный файл создан: {self.main_file}")
        
        # ТЕПЕРЬ ЗАМЕНЯЕМ ТЕКСТ В ГЛАВНОМ ФАЙЛЕ

        
        self.replace_text()
        
        
        dxf_to_jpg(self.main_file, self.png_file)
        png_to_pdf(self.png_file, self.pdf_file) # type: ignore
        add_watermark(self.pdf_file, self.pdf_file)
        
        
        
     
        
        

    def build_all(self) -> str:
        """
        Полный цикл создания главного DXF файла
        """
        cprint(f"\n{'='*60}", 'cyan', bold=True)
        cprint("🔨 СОЗДАНИЕ ЧЕРТЕЖА ДВЕРИ (ДИНАМИЧЕСКОЕ ПОЗИЦИОНИРОВАНИЕ)", 'cyan', bold=True)
        cprint(f"{'='*60}", 'cyan', bold=True)
        logger.info("="*60)
        logger.info("🔨 СОЗДАНИЕ ЧЕРТЕЖА ДВЕРИ (ДИНАМИЧЕСКОЕ ПОЗИЦИОНИРОВАНИЕ)")
        logger.info("="*60)
        
        # ПРИНУДИТЕЛЬНО УСТАНАВЛИВАЕМ ОТСТУПЫ
        cprint("📌 Установка отступов:", 'blue', bold=True)
        logger.info("📌 Установка отступов:")
        cprint(f"   SPACING_X = {self.SPACING_X}", 'white')
        cprint(f"   SPACING_Y = {self.SPACING_Y}", 'white')
        cprint(f"   MARGIN = {self.MARGIN}", 'white')
        logger.info(f"   SPACING_X = {self.SPACING_X}")
        logger.info(f"   SPACING_Y = {self.SPACING_Y}")
        logger.info(f"   MARGIN = {self.MARGIN}")
        
        cprint("📌 Шаг 1/4: Создание наружного вида (вид спереди)", 'blue', bold=True)
        logger.info("📌 Шаг 1/4: Создание наружного вида (вид спереди)")
        self.build_out()
        
        cprint("📌 Шаг 2/4: Создание внутреннего вида (вид изнутри)", 'blue', bold=True)
        logger.info("📌 Шаг 2/4: Создание внутреннего вида (вид изнутри)")
        self.build_in()
        
        cprint("📌 Шаг 3/4: Создание разрезов", 'blue', bold=True)
        logger.info("📌 Шаг 3/4: Создание разрезов")
        self.build_cuts()
        
        cprint("📌 Шаг 4/4: Сборка главного файла", 'blue', bold=True)
        logger.info("📌 Шаг 4/4: Сборка главного файла")
        self.assemble_main()
        
        # ===== СОХРАНЕНИЕ В БАЗУ ДАННЫХ =====
        cprint("📌 Шаг 5/5: Сохранение в базу данных", 'blue', bold=True)
        logger.info("📌 Шаг 5/5: Сохранение в базу данных")
        if self.save_to_database():
            cprint(f"   ✅ Заказ сохранен в БД (ID: {self.contract_ID})", 'green')
            logger.info(f"   ✅ Заказ сохранен в БД (ID: {self.contract_ID})")
        else:
            cprint(f"   ⚠️ Ошибка сохранения заказа в БД", 'yellow')
            logger.warning(f"   ⚠️ Ошибка сохранения заказа в БД")
        
        cprint(f"\n{'='*60}", 'green', bold=True)
        cprint("✅ ГОТОВО!", 'green', bold=True)
        cprint(f"{'='*60}", 'green', bold=True)
        cprint(f"📄 Главный файл: {self.main_file}", 'cyan')
        cprint(f"🆔 ID заказа: {self.contract_ID}", 'cyan')
        cprint(f"{'='*60}", 'green', bold=True)
        logger.info("="*60)
        logger.info("✅ ГОТОВО!")
        logger.info("="*60)
        logger.info(f"📄 Главный файл: {self.main_file}")
        logger.info(f"🆔 ID заказа: {self.contract_ID}")
        logger.info("="*60)
        
        return self.contract_ID

    def add_bottom_text(self):
        """
        Добавляет текст внизу, справа от горизонтального разреза
        """
        cprint("   Добавление текста внизу", 'blue')
        logger.info("   Добавление текста внизу")
        
        if self.doc is None or self.msp is None:
            cprint("   ❌ Документ не инициализирован", 'red')
            logger.error("   ❌ Документ не инициализирован")
            return
        
        # Получаем позицию горизонтального разреза
        horiz_pos = self.drawings['horiz'].position
        horiz_width = self.drawings['horiz'].width
        
        # Текст размещаем справа от горизонтального разреза с отступом
        x = horiz_pos[0] + horiz_width + 200  # Отступ 200 от правого края горизонтального разреза
        
        # Текст размещаем на том же уровне, что и горизонтальный разрез
        y = horiz_pos[1]+560  # На одном уровне с горизонтальным разрезом
        
        cprint(f"      Позиция текста: X={x:.0f}, Y={y:.0f}", 'cyan')
        logger.info(f"      Позиция текста: X={x:.0f}, Y={y:.0f}")
        cprint(f"      Горизонтальный разрез: X({horiz_pos[0]:.0f}..{horiz_pos[0]+horiz_width:.0f})", 'cyan')
        logger.info(f"      Горизонтальный разрез: X({horiz_pos[0]:.0f}..{horiz_pos[0]+horiz_width:.0f})")
        
        # Подготавливаем текст
        text_lines = [
            "Данный эскиз не отображает всех особенностей",
            "конструкции, комплектации и дизайна изделия,",
            "не влияющих на заявленные в тех.требованиях",
            "параметры заказа и потребительские свойства",
            "изделия(ий).",
            "",
            "",
            f"Эскиз подготовил: ________________{self.data.get('date', '')}",
            "",
            f"Менеджер:_____________{self.data.get('manager', 'Неизвестный')}",
            "",
            f"Утвердил__________{self.data.get('order_name', '')} {self.data.get('date', '')}"
        ]
        
        # Размер шрифта и отступы
        FONT_SIZE = 35
        LINE_SPACING = 45  # Отступ между строками
        
        # Добавляем текст построчно
        line_count = 0
        current_y = y
        
        for line in text_lines:
            if line.strip():  # Если строка не пустая
                self.msp.add_text(
                    line,
                    dxfattribs={
                        'height': FONT_SIZE,
                        'insert': (x, current_y),
                        'layer': "TEXT_LAYER",
                        'style': "STANDARD"
                    }
                )
                logger.debug(f"         Добавлен текст: '{line[:30]}...' в ({x:.0f}, {current_y:.0f})")
                line_count += 1
            current_y -= LINE_SPACING  # Отступ между строками
        
        cprint(f"      Добавлено {line_count} строк текста (шрифт {FONT_SIZE})", 'green')
        logger.info(f"      Добавлено {line_count} строк текста (шрифт {FONT_SIZE})")
        return line_count

    def calc_spec_size(self):
        # Функция возвращает табличные размеры w0, w1, h0, h2 в зависимости от типа двери
        current_width=int(self.data['01_Ширина'])
        current_height=int(self.data['02_Высота'])
        w1=0
        h2=0

        if self.data['model']=="ULTIMATUM PRO PP" or self.data['model']=="ULTIMATUM PRO MP":
            w1= current_width-108
            h2=current_height+55
        elif self.data['model'] =='SNEGIR ARCTIC MP' or self.data['model'] =='SNEGIR ARCTIC PP':
            w1=current_width-120
            h2=current_height+56.5
        elif self.data['model'] =='SNEGIR PRO MP' or self.data['model'] =='SNEGIR PRO PP' or "DIAMOND" in self.data['model'] or self.data['model'] =='SNEGIR PRO-C MP' or self.data['model'] =='SNEGIR PRO-C PP':
            w1=current_width-130
            h2=current_height+65
        elif self.data['model'] == 'TAU LT PP' or self.data['model'] == 'TAU LT MP':
            w1=current_width-120
            h2=current_height+61  
        elif 'S.OMEGA PRO' in self.data['model'] or "CYBER PRO" in self.data['model']:
            w1=current_width-120
            h2=current_height+61        
        elif 'DELTA PRO' in self.data['model'] or 'DELTA 100' in self.data['model']:
            w1=current_width-108
            h2=current_height+55
        elif 'NEXT' in self.data['model'] or 'Edge' in self.data['model']:
            w1=current_width-120
            h2=current_height+61
            
        elif 'PROFESSOR-4' in self.data['model']:
            w1=current_width-80
            h2=current_height+61

        return w1, h2 

    def replace_text(self):
        """
        Заменяет текст в главном файле main.dxf
        """
        cprint("📝 Замена текста в главном файле", 'blue')
        logger.info("📝 Замена текста в главном файле")
        
        w1, h2 = self.calc_spec_size()
        
        # Создаем замены для всех текстовых полей
        replacements = {
            'WIDTH 0': str(self.data['01_Ширина']),
            'vff': str(self.data['vff']),
            'zff': str(self.data['zff']),
            'pff': str(self.data['pff']),
            'H0': str(self.data['02_Высота']),
            'WIDTH 1': str(w1),
            'H2': str(h2),
            'HEAD': str(self.data['height_head'])
        }
        
        cprint(f"   Замены ({len(replacements)} шт.):", 'cyan')
        logger.info(f"   Замены ({len(replacements)} шт.):")
        for old, new in replacements.items():
            cprint(f"      '{old}' -> '{new}'", 'white')
            logger.info(f"      '{old}' -> '{new}'")
        
        # Загружаем главный файл
        doc = ezdxf.readfile(str(self.main_file)) # type: ignore
        msp = doc.modelspace()
        
        # Счетчики для статистики
        text_replaced = 0
        mtext_replaced = 0
        
        # Заменяем текст в пространстве модели
        for entity in msp:
            if entity.dxftype() == 'TEXT':
                original = entity.dxf.text
                new_text = original
                changed = False
                
                for old, new in replacements.items():
                    if old in new_text:
                        new_text = new_text.replace(old, new)
                        changed = True
                
                if changed:
                    entity.dxf.text = new_text
                    text_replaced += 1
                    logger.debug(f"      TEXT: '{original}' -> '{new_text}'")
            
            elif entity.dxftype() == 'MTEXT':
                original = entity.dxf.text
                new_text = original
                changed = False
                
                for old, new in replacements.items():
                    if old in new_text:
                        new_text = new_text.replace(old, new)
                        changed = True
                
                if changed:
                    entity.dxf.text = new_text
                    mtext_replaced += 1
                    logger.debug(f"      MTEXT: '{original[:30]}...' -> '{new_text[:30]}...'")
        
        # Также проверяем текст в блоках
        for block in doc.blocks:
            if block.name != '*Model_Space':
                for entity in block:
                    if entity.dxftype() == 'TEXT':
                        original = entity.dxf.text
                        new_text = original
                        changed = False
                        
                        for old, new in replacements.items():
                            if old in new_text:
                                new_text = new_text.replace(old, new)
                                changed = True
                        
                        if changed:
                            entity.dxf.text = new_text
                            text_replaced += 1
                            logger.debug(f"      TEXT в блоке '{block.name}': '{original}' -> '{new_text}'")
        
        # Сохраняем файл
        doc.saveas(str(self.main_file))
        
        total = text_replaced + mtext_replaced
        cprint(f"   ✅ Заменено: TEXT={text_replaced}, MTEXT={mtext_replaced}, Всего={total}", 'green')
        logger.info(f"   ✅ Заменено: TEXT={text_replaced}, MTEXT={mtext_replaced}, Всего={total}")
        
        return total
    
    def wrap_text(self, text, max_length=38):
        """Переносит длинный текст на несколько строк"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        # Убираем маркер "• " из подсчета длины, если он есть
        prefix = "• " if text.startswith("• ") else ""
        if prefix:
            text_without_prefix = text[2:]
            words = text_without_prefix.split()
        else:
            prefix = ""
            words = text.split()
        
        for word in words:
            # Проверяем длину с учетом пробела
            if current_length + len(word) + (1 if current_line else 0) <= max_length:
                current_line.append(word)
                current_length += len(word) + (1 if current_line else 0)
            else:
                if current_line:
                    lines.append(prefix + ' '.join(current_line))
                    prefix = "  "  # Для перенесенных строк используем отступ
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(prefix + ' '.join(current_line))
        
        return lines
    
    
    def add_left_text(self):
        """
        Добавляет текст слева от вида снаружи, на уровне верхнего ряда чертежей
        Используется тот же текст, что и в оригинальном коде
        """
        cprint("   Добавление текста слева от вида снаружи", 'blue')
        logger.info("   Добавление текста слева от вида снаружи")
        
        if self.doc is None or self.msp is None:
            cprint("   ❌ Документ не инициализирован", 'red')
            logger.error("   ❌ Документ не инициализирован")
            return
        
        # Создаем текстовые стили, если их нет
        if "BOLD_TEXT" not in self.doc.styles:
            # Создаем стиль для жирного текста с Arial
            bold_style = self.doc.styles.new("BOLD_TEXT", dxfattribs={
                'font': "Arial.ttf",  # Имя файла шрифта
                'width': 1.0,
                'oblique': 0,
                'height': 0  # 0 означает нефиксированная высота
            })
            # Устанавливаем расширенные данные для жирного шрифта
            bold_style.set_extended_font_data(family='Arial', italic=False, bold=True)  # [citation:3][citation:4]
        
        if "ITALIC_TEXT" not in self.doc.styles:
            italic_style = self.doc.styles.new("ITALIC_TEXT", dxfattribs={
                'font': "Arial.ttf",
                'width': 1.0,
                'oblique': 15,  # Наклон для курсива
                'height': 0
            })
            italic_style.set_extended_font_data(family='Arial', italic=True, bold=False)
        
        if "NORMAL_TEXT" not in self.doc.styles:
            normal_style = self.doc.styles.new("NORMAL_TEXT", dxfattribs={
                'font': "Arial.ttf",
                'width': 1.0,
                'oblique': 0,
                'height': 0
            })
            normal_style.set_extended_font_data(family='Arial', italic=False, bold=False)
        
        # Получаем позицию вида снаружи (вид спереди)
        out_pos = self.drawings['out'].position
        out_height = self.drawings['out'].height
        
        # Текст размещаем слева от вида снаружи с отступом
        x = out_pos[0] - 1500  # Отступ влево (как в оригинале -1900)
        
        # Начинаем с уровня верхнего края вида снаружи
        y = out_pos[1] + out_height  # Немного ниже верхнего края
        
        cprint(f"      Начальная позиция: X={x:.0f}, Y={y:.0f}", 'cyan')
        logger.info(f"      Начальная позиция: X={x:.0f}, Y={y:.0f}")
        
        # Определяем сторону открывания
        mont_string = ''
        if 'НАКЛ' in self.data.get('09_Монтаж', '') or 'ФРАМ' in self.data.get('09_Монтаж', ''):
            mont_string1 = 'в наклад со стороны '
        elif 'ПРОЕМ' in self.data.get('09_Монтаж', '') or 'комб' in self.data.get('09_Монтаж', '') :
            mont_string1 = 'в проем со стороны '
            
        mont_string2 = 'мест общего пользования'    

        
        if 'L' in self.data.get('03_Петли', ''):
            side1 = 'Левое'
            side2 = 'Правое'
        else:
            side1 = 'Правое'
            side2 = 'Левое'
        
        # Создаем слой для текста, если его нет
        if "TEXT_LAYER" not in self.doc.layers:
            self.doc.layers.new(name="TEXT_LAYER", dxfattribs={'color': 7})
        
        # ===== БЛОК 1: Основная информация =====
        text_block1 = [
            f"ТДОТ-{self.data.get('TDOT', '')}",
            f"Модель: {self.data.get('model', '')}  {self.data.get('01_Ширина', '')}*{self.data.get('02_Высота', '')} {self.data.get('03_Петли', '')}"]
            
        
        for line in text_block1:
            if line:
                self.msp.add_text(
                    line,
                    dxfattribs={
                        'height': 40,
                        'insert': (x, y),
                        'layer': "TEXT_LAYER",
                        'style': "BOLD_TEXT"  # Используем жирный стиль
                    }
                )
                logger.debug(f"         Текст: '{line[:30]}...' в ({x:.0f}, {y:.0f})")
            y -= 50
        
        y -= 20  # Дополнительный отступ после блока
        
        # ===== БЛОК 2: Описание монтажа =====
        text_block2 = [
            f"Дверной блок наружного открывания, ",
            f"{mont_string1}",
            f"{mont_string2}",
            f"Изображено {side1} исполнение дверного",
            f"блока  / {side2} зеркально."
        ]
        
        for line in text_block2:
            if line:
                self.msp.add_text(
                    line,
                    dxfattribs={
                        'height': 40,
                        'insert': (x, y),
                        'layer': "TEXT_LAYER"
                    }
                )
                logger.debug(f"         Текст: '{line[:30]}...' в ({x:.0f}, {y:.0f})")
            y -= 50
        
        y -= 100  # Дополнительный отступ после блока
        
        # ===== БЛОК 3: Наружная отделка =====
        # Заголовок
        self.msp.add_text(
            "Наружная отделка:",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER",
                'style': "BOLD_TEXT"  # Используем жирный стиль
            }
        )
        y -= 60
        
        # Детали
        text_block3 = [
            f" Цвет: {self.data.get('04_Лицо (цвет)', '')}",
            f" Рисунок: {self.data.get('05_Лицо (рисунок)', '')}"
        ]
        
        for line in text_block3:
            self.msp.add_text(
                line,
                dxfattribs={
                    'height': 40,
                    'insert': (x, y),
                    'layer': "TEXT_LAYER"
                }
            )
            y -= 55
        
        y -= 100  # Дополнительный отступ
        
        # ===== БЛОК 4: Внутренняя отделка =====
        self.msp.add_text(
            "Внутренняя отделка:",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER",
                'style': "BOLD_TEXT"  # Используем жирный стиль
            }
        )
        y -= 55
        
        text_block4 = [
            f" Цвет: {self.data.get('06_Внутр. отделка (цвет)', '')}",
            f" Рисунок: {self.data.get('07_Внутр. отделка (рисунок)', '')}"
        ]
        
        for line in text_block4:
            self.msp.add_text(
                line,
                dxfattribs={
                    'height': 40,
                    'insert': (x, y),
                    'layer': "TEXT_LAYER"
                }
            )
            y -= 55
        
        y -= 80
        
        # ===== БЛОК 5: Фурнитура =====
        self.msp.add_text(
            "Фурнитура: ",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER",
                'style': "BOLD_TEXT"  # Используем жирный стиль
            }
        )
        y -= 55
        
        self.msp.add_text(
            f" {self.data.get('08_Фурнитура', '')}",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER"
            }
        )
        y -= 70
        
        # ===== БЛОК 6: Наличник =====
        self.msp.add_text(
            "Наличник: ",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER",
                'style': "BOLD_TEXT"  # Используем жирный стиль
            }
        )
        y -= 55
        
        self.msp.add_text(
            f" {self.data.get('10_Обналичка', '')}  {self.data.get('11_Обналичка (цвет)', '')}",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER"
            }
        )
        
        # ===== БЛОК 7: Фальшфрамуга (если есть) =====
        if (self.data.get('zff', 0) > 85 or 
            self.data.get('pff', 0) > 85 or 
            self.data.get('vff', 0) > 85):
            y -= 100
            
            ff_lines = [
                f"Фальшфрамуга:",
                f" ПЕТЛЕВАЯ:",
                f"{self.data.get('pff', '')}, {int(self.data.get('02_Высота', 0)) + int(self.data.get('vff', 0))}, {self.data.get('03_Петли', '')}, {self.data.get('04_Лицо (цвет)', '')}, НАКЛ ",
                f" ВЕРХНЯЯ:",
                f"{self.data.get('01_Ширина', '')}, {self.data.get('vff', '')}, {self.data.get('03_Петли', '')}, {self.data.get('04_Лицо (цвет)', '')}, НАКЛ ",
                f" ЗАМКОВАЯ:",
                f"{self.data.get('zff', '')}, {int(self.data.get('02_Высота', 0)) + int(self.data.get('vff', 0))}, {self.data.get('03_Петли', '')}, {self.data.get('04_Лицо (цвет)', '')}, НАКЛ "
            ]
            
            for line in ff_lines:
                self.msp.add_text(
                    line,
                    dxfattribs={
                        'height': 40,
                        'insert': (x, y),
                        'layer': "TEXT_LAYER"
                    }
                )
                y -= 50
            y -= 200
        else:
            y -= 100
        
        # ===== БЛОК 8: Опции =====
        self.msp.add_text(
            "Опции:",
            dxfattribs={
                'height': 40,
                'insert': (x, y),
                'layer': "TEXT_LAYER",
                'style': "BOLD_TEXT"  # Используем жирный стиль
            }
        )
        y -= 50
        
        options = self.data.get('options', [])
        if options:
            if isinstance(options, str):
                options = [options]
            for option in options:
                lines = self.wrap_text(option, max_length=38)
                for line in lines:
                    self.msp.add_text(
                        line,
                        dxfattribs={
                            'height': 40,
                            'insert': (x, y),
                            'layer': "TEXT_LAYER"
                        }
                    )
                    y -= 50
            y -= 70
        else:
            y -= 120
        
        # ===== БЛОК 9: Примечания =====
        notes = self.data.get('notes', '')
        if notes:
            self.msp.add_text(
                "Примечание:",
                dxfattribs={
                    'height': 40,
                    'insert': (x, y),
                    'layer': "TEXT_LAYER",
                    'style': "BOLD_TEXT"  # Используем жирный стиль
                }
            )
            y -= 50
            
            if isinstance(notes, str):
                # Разбиваем длинные примечания на строки по 50 символов
                words = notes.split()
                lines = []
                current_line = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) < 50:
                        current_line.append(word)
                        current_length += len(word) + 1
                    else:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = len(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                for line in lines:
                    self.msp.add_text(
                        line,
                        dxfattribs={
                            'height': 40,
                            'insert': (x, y),
                            'layer': "TEXT_LAYER"
                        }
                    )
                    y -= 50
        
        # ===== БЛОК 10: Цена и количество =====
        if self.data.get('TDOT', '') != '':
            y -= 100
            
            self.msp.add_text(
                "Количество дверей в заказе:",
                dxfattribs={
                    'height': 40,
                    'insert': (x, y),
                    'layer': "TEXT_LAYER",
                    'style': "BOLD_TEXT"  # Используем жирный стиль
                }
            )
            
            # Количество справа
            self.msp.add_text(
                f"{str(self.data.get('count', 1))} шт.",
                dxfattribs={
                    'height': 40,
                    'insert': (x + 1100, y),
                    'layer': "TEXT_LAYER",
                    'style': "BOLD_TEXT"  # Используем жирный стиль
                }
            )
            y -= 50
            
            # Цена и сумма
            cost = float(self.data.get('cost', 0))
            count = int(self.data.get('count', 1))
            total = cost * count
            
            price_lines = [
                f"",
                f"Цена изделия: {cost:.2f} руб.",
                f"Сумма заказа: {total:.2f} руб."
            ]
            
            for line in price_lines:
                if line:
                    self.msp.add_text(
                        line,
                        dxfattribs={
                            'height': 40,
                            'insert': (x, y),
                            'layer': "TEXT_LAYER"
                        }
                    )
                y -= 50
            
            # ID заказа внизу
            self.msp.add_text(
                f"ID заказа: {self.contract_ID}",
                dxfattribs={
                    'height': 40,
                    'insert': (x, 409),
                    'layer': "TEXT_LAYER"
                }
            )
        
        cprint(f"   ✅ Текст слева добавлен", 'green')
        logger.info(f"   ✅ Текст слева добавлен")
    
    
    
        
    def _add_text_block(self, text_lines, x, y, bold=False, height=40.0):
        """
        Вспомогательный метод для добавления блока текста
        
        Args:
            text_lines: список строк текста
            x, y: координаты вставки
            bold: жирный шрифт или нет
            height: высота текста
        """
        if not text_lines:
            return
        
        # Если text_lines - строка, преобразуем в список
        if isinstance(text_lines, str):
            text_lines = [text_lines]
        
        current_y = y
        
        for line in text_lines:
            if line.strip() or line == "":  # Пустые строки тоже добавляем для соблюдения отступов
                self.msp.add_text( # type: ignore
                    line,
                    dxfattribs={
                        'height': height,
                        'insert': (x, current_y),
                        'layer': "TEXT_LAYER",
                        'style': "KTEXTSTYLE" if bold else "STANDARD"
                    }
                )
                logger.debug(f"         Текст: '{line[:30]}...' в ({x:.0f}, {current_y:.0f})")
            current_y -= height * 1.5  # Отступ между строками
  
   
    

    
    # Для тестирования
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    
    test_data = {
        'path_to_order': str(Path.home() / 'TEST'),
        'model': 'DELTA 100 MP',
        '01_Ширина': 1000,
        '02_Высота': 2200,
        '03_Петли': 'L',
        '04_Лицо (цвет)': ' КТ Белый',
        '05_Лицо (рисунок)': 'Busoni',
        '06_Внутр. отделка (цвет)': 'Белый',
        '07_Внутр. отделка (рисунок)': 'Castle',
        '08_Фурнитура': 'ЧКВ_AP15_AP15',
        '09_Монтаж': 'НАКЛ',
        '10_Обналичка': 'НУ-1',
        'peep': True,
        'peep_offset': False,
        'vff': 300,
        'zff': 300,
        'pff': 350,
        'head': False,
        'height_head': 0,
        'TDOT': '12345',
        'cost': 15000,
        'count': 1,
        'manager': 'СосновцевДА',
        'date': '19.03.2026',
        'contract_ID': 'TEST-001'
    }
    
    try:
        maker = MakeDoorDXF(test_data)
        id = maker.build_all()
        cprint(f"✅ Тест успешно завершен", 'green')
        logger.info(f"✅ Тест успешно завершен")
        
        
    except Exception as e:
        cprint(f"❌ Ошибка: {e}", 'red', bold=True)
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

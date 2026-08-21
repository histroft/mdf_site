"""
Модуль для добавления обналички и фальшфрамуги к DXF чертежу наружной двери
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys


project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"📁 Добавлен путь: {project_root}")
from make_order.dxf_modules.base import DXFDocument
import logging
logger = logging.getLogger(__name__)
logging.getLogger('ezdxf').setLevel(logging.WARNING)


class AddFFOut:
    """
    Класс для добавления обналички и фальшфрамуги к чертежу наружной двери
    """
    
    
    
    
    # Константы
    TRIM_STANDARD = 85      # стандартный размер обналички
    TRIM_CUT = 36           # обрезной размер
    BASE_LINE_OFFSET = 1    # смещение базовой линии
    PATTERN_OFFSET = 2.5    # коррекция для рисунка
    HIGH_FF_THRESHOLD = 700 # порог для добавления дополнительной линии
    
    # # Список рисунков типа L1 (для определения вертикальных линий)
    # L1_PICTURES = [
    #     'D-L1', 'UT-L1', 'D-L8', 'D-23', 'D-33', 'D-36', 'UT-L5','UT-S1']
    #     'D-S12', 'UT-S1', 'D-S12', 'UT-S12', 'D-S11', 'UT-S11',
    #     'D-W1', 'UT-W1', 'D-W11', 'UT-W11', 'T-L1', 'OP-L1', 'CBR-21',
    #     'T-L8', 'OP-L8', 'CBR-22', 'T-23', 'OP-L7', 'T-33', 'OP-L6',
    #     'T-36', 'OP-L9', 'T-S12', 'OP-S12', 'CBR-S12', 'T-S12', 'OP-S12',
    #     'CBR-S12', 'T-S11', 'OP-S11', 'CBR-S11', 'T-W1', 'OP-W1', 'CBR-W1',
    #     'T-W11', 'OP-W11', 'CBR-W11', 'L1', 'S12', 'S11', 'W1', 'S1', 'W11'
    # ]
    
    # S12_PICTURES=[]
    
    
    # Карта количества линий для рисунка на фальшфрамуге
    LINE_COUNT_MAP = {
        (0, 150): 3,
        (150, 200): 5,
        (200, 250): 7,
        (250, 300): 9,
        (300, 350): 10,
        (350, 400): 12,
        (400, 450): 14,
        (450, 500): 15,
        (500, 550): 17,
    }
    
    def __init__(self, data: Dict[str, Any], doc: DXFDocument):
        """
        Инициализация построителя обналички
        
        Args:
            data: словарь с данными заказа
            doc: открытый DXF документ
        """
        self.data = data
        self.doc = doc
        self.msp = doc.msp
        self.finish_up_size = 0
        
        logger.info("🏗️ AddFFOut: НАЧАЛО РАБОТЫ")
        
        self._extract_data()
        self._get_bounds()  # Получаем границы чертежа
        self._calculate_trim_sizes()
        self.build()
        
        logger.info(f"✅ AddFFOut: РАБОТА ЗАВЕРШЕНА, finish_up_size={self.finish_up_size:.1f}")
    
    def _extract_data(self):
        """Извлекает данные из словаря"""
        self.model = self.data.get('model', '')
        self.width = float(self.data.get('01_Ширина', 0))
        self.height = float(self.data.get('02_Высота', 0))
        self.install_type = self.data.get('09_Монтаж', '')
        self.side = self.data.get('03_Петли', '')
        self.vff = int(self.data.get('vff', 0))
        self.zff = int(self.data.get('zff', 0))
        self.pff = int(self.data.get('pff', 0))
        self.ff_pic = self.data.get('ff_pic', '')
        self.options = self.data.get('options', [])
        self.out_pic = self.data.get('05_Лицо (рисунок)', '')
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
        """Вычисляет размеры обналички (АБСОЛЮТНЫЕ)"""
        is_in_proem = self.install_type == 'ПРОЕМ'
        is_right_door = 'R' in self.side
        
        # Верхняя часть - размер вверх от верхней границы
        if is_in_proem or 'Обналичка обрезная сверху' in self.options:
            self.up_part = self.TRIM_CUT
        else:
            self.up_part = self.vff if self.vff else self.TRIM_STANDARD
        
        # Левая часть - размер влево от левой границы
        if is_in_proem or 'Обналичка обрезная слева' in self.options:
            self.left_part = self.TRIM_CUT
        else:
            ff_size = self.zff if is_right_door else self.pff
            self.left_part = ff_size if ff_size else self.TRIM_STANDARD
        
        # Правая часть - размер вправо от правой границы
        if is_in_proem or 'Обналичка обрезная справа' in self.options:
            self.right_part = self.TRIM_CUT
        else:
            ff_size = self.pff if is_right_door else self.zff
            self.right_part = ff_size if ff_size else self.TRIM_STANDARD
        
        logger.debug(f"   📐 Размеры обналички (абсолютные):")
        logger.debug(f"      левая: {self.left_part} мм влево")
        logger.debug(f"      правая: {self.right_part} мм вправо")
        logger.debug(f"      верх: {self.up_part} мм вверх")
    
    def build(self):
        """Основной метод построения обналички"""
        logger.info("   🛠️ Построение обналички")
        
        
        self._draw_up_part()
        if self.ff_pic and self.vff>85:
            self._add_lines_to_up_part()
        
        self._draw_left_part()
        self._draw_right_part()
        
        
        if self.ff_pic in ('L1', 'S12'):
            self._add_lines_to_left_part()
            self._add_lines_to_right_part()
        
        self.finish_up_size = self.max_y + self.up_part
        logger.debug(f"   📏 finish_up_size = {self.finish_up_size:.1f}")
    
    def _draw_left_part(self):
        """Рисует левую часть обналички от левой границы чертежа"""
        
        # Нижняя горизонталь
        self.doc.add_line(self.min_x, self.min_y, 
                         self.min_x - self.left_part, self.min_y, color=1)
        
        # Вертикаль
        self.doc.add_line(self.min_x - self.left_part, self.min_y,
                         self.min_x - self.left_part, self.max_y + self.up_part, color=1)
        
        # Верхняя горизонталь
        self.doc.add_line(self.min_x - self.left_part, self.max_y + self.up_part,
                         self.min_x, self.max_y + self.up_part, color=1)
        
        # Дополнительная линия для высокой фальшфрамуги
        if self.vff >= self.HIGH_FF_THRESHOLD:
            self.doc.add_line(self.min_x, self.max_y,
                             self.min_x - self.left_part, self.max_y, color=1)
    
    def _draw_right_part(self):
        """Рисует правую часть обналички от правой границы чертежа"""  
        # Нижняя горизонталь
        self.doc.add_line(self.max_x, self.min_y,
                         self.max_x + self.right_part, self.min_y, color=1)
        
        # Вертикаль
        self.doc.add_line(self.max_x + self.right_part, self.min_y,
                         self.max_x + self.right_part, self.max_y + self.up_part, color=1)
        
        # Верхняя горизонталь
        self.doc.add_line(self.max_x + self.right_part, self.max_y + self.up_part,
                         self.max_x, self.max_y + self.up_part, color=1)
        
        if self.vff >= self.HIGH_FF_THRESHOLD:
            self.doc.add_line(self.max_x, self.max_y,
                             self.max_x + self.right_part, self.max_y, color=1)
    
    def _draw_up_part(self):
        """Рисует верхнюю часть обналички от верхней границы чертежа"""
        logger.debug(f"   --- Верхняя часть: от Y={self.max_y:.1f} вверх на {self.up_part} мм")
        
        # Левая вертикаль
        self.doc.add_line(self.min_x, self.max_y,
                         self.min_x, self.max_y + self.up_part, color=1)
        
        # Верхняя горизонталь
        self.doc.add_line(self.min_x, self.max_y + self.up_part,
                         self.max_x, self.max_y + self.up_part, color=1)
        
        # Правая вертикаль
        self.doc.add_line(self.max_x, self.max_y + self.up_part,
                         self.max_x, self.max_y, color=1)
        
        # Добавление надставки
        self._draw_head()
        
        
    
    def _draw_head(self):
        """Рисует надставку, если она есть"""
        if not self.head:
            return
        
        logger.debug(f"   --- Надставка: высота {self.height_head}")
        
        start_x = self.min_x - self.left_part
        start_y = self.max_y + self.up_part
        end_x = self.max_x + self.right_part
        end_y = start_y + self.height_head
        
        # Левая вертикаль надставки
        self.doc.add_line(start_x, start_y, start_x, end_y, color=1)
        
        # Верхняя горизонталь надставки
        self.doc.add_line(start_x, end_y, end_x, end_y, color=1)
        
        # Правая вертикаль надставки
        self.doc.add_line(end_x, end_y, end_x, start_y, color=1)
    
    def _calc_line_count(self, size: int) -> int:
        """Вычисляет количество линий для рисунка"""
        for (low, high), count in self.LINE_COUNT_MAP.items():
            if low <= size < high:
                return count
        return 19
    
    def _add_lines_to_left_part(self):
        """Добавляет линии рисунка на левую часть"""
        size = self.left_part
        if size == 0:
            return
        
        count = self._calc_line_count(size)
        step = (size + 3) / count
        
        base_x = self.min_x - self.BASE_LINE_OFFSET
        self.doc.add_line(base_x, self.min_y, base_x, self.max_y + self.up_part, color=6)
        
        logger.debug(f"   --- Добавление линий на левую часть: {count} линий")
        
        for i in range(1, count + 1):
            if i == 1:
                offset = step - self.PATTERN_OFFSET
            elif i == count:
                offset = (step - self.PATTERN_OFFSET) + (count - 2) * step + (step - self.PATTERN_OFFSET)
            else:
                offset = (step - self.PATTERN_OFFSET) + (i - 1) * step
            
            x = base_x - offset
            self.doc.add_line(x, self.min_y, x, self.max_y + self.up_part, color=6)
    
    def _add_lines_to_right_part(self):
        """Добавляет линии рисунка на правую часть"""
        size = self.right_part
        if size == 0:
            return
        
        count = self._calc_line_count(size)
        step = (size + 3) / count
        
        base_x = self.max_x + self.BASE_LINE_OFFSET
        self.doc.add_line(base_x, self.min_y, base_x, self.max_y + self.up_part, color=6)
        logger.debug(f"   --- Добавление линий на правую часть: {count} линий")
        for i in range(1, count + 1):
            if i == 1:
                offset = step - self.PATTERN_OFFSET
            elif i == count:
                offset = (step - self.PATTERN_OFFSET) + (count - 2) * step + (step - self.PATTERN_OFFSET)
            else:
                offset = (step - self.PATTERN_OFFSET) + (i - 1) * step
            
            x = base_x + offset
            self.doc.add_line(x, self.min_y, x, self.max_y + self.up_part, color=6)

    
    
    
    def _add_lines_to_up_part(self):
        """Добавляет вертикальные линии на верхнюю часть для рисунка L1"""
        print('\n=== _add_lines_to_up_part() ===')
        print(f"ff_pic={self.ff_pic}, vff={self.vff}")
        
        if self.ff_pic != 'L1':
            return
        
        if self.vff <= 85:
            return
        
        # Получаем вертикальные линии с двери
        x_points = self._get_vertical_lines_from_door()
        
        if not x_points:
            print("  ⚠️ Вертикальные линии на двери не найдены")
            return
        
        print(f"  Найдено линий на двери: {len(x_points)}")
        
        # Фильтруем и очищаем точки
        clean_points = self._clean_points(x_points)
        print(f"  После очистки: {len(clean_points)} линий")
        print(f"  Координаты: {clean_points}")
        
        # Дополняем паттерн до полной ширины
        all_lines_x = self._extend_pattern_to_full_width(clean_points)
        
        print(f"  После дополнения: {len(all_lines_x)} линий")
        print(f"  Диапазон X: [{min(all_lines_x):.1f}, {max(all_lines_x):.1f}]")
        
        # Рисуем линии
        y_start = self.max_y
        y_end = self.max_y + self.up_part
        
        for x in all_lines_x:
            if self.min_x - 5 <= x <= self.max_x + 5:
                self.doc.add_line(x, y_start, x, y_end, color=6)
        
        print(f"  ✅ Добавлено {len(all_lines_x)} вертикальных линий")

    #============================================================================    
    def _add_lines_to_up_part(self):
        """Добавляет вертикальные линии на верхнюю часть"""
        print('\n=== _add_lines_to_up_part() ===')
        print(f"ff_pic={self.ff_pic}, vff={self.vff}")
        
        if self.vff <= 85:
            print(f"  vff={self.vff} <= 85, линии не нужны")
            return
        
        # Получаем вертикальные линии с двери
        x_points = self._get_vertical_lines_from_door()
        
        if not x_points:
            print("  ⚠️ Вертикальные линии на двери не найдены")
            return
        
        print(f"  Найдено линий на двери: {len(x_points)}")
        
        # Определяем, какие линии рисовать
        if self.ff_pic == 'L1':
            # Для L1: дополняем паттерн до полной ширины
            print("  Режим L1: дополнение паттерна до полной ширины")
            all_lines_x = self._extend_pattern_to_full_width(x_points)
        else:
            # Для всех остальных рисунков (S12, S1, W1 и т.д.): 
            # переносим только существующие линии
            print(f"  Режим {self.ff_pic}: перенос только существующих линий")
            all_lines_x = x_points
        
        print(f"  Будет нарисовано линий: {len(all_lines_x)}")
        
        # Рисуем линии
        y_start = self.max_y
        y_end = self.max_y + self.up_part
        
        for x in all_lines_x:
            if self.min_x - 5 <= x <= self.max_x + 5:
                self.doc.add_line(x, y_start, x, y_end, color=6)
        
        print(f"  ✅ Добавлено {len(all_lines_x)} вертикальных линий")

    def _get_vertical_lines_from_door(self) -> List[float]:
        """
        Получает координаты X всех вертикальных линий с рисунка двери
        """
        x_coords = set()
        
        print("  Поиск вертикальных линий на двери...")
        
        for entity in self.msp:
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                
                # Проверяем вертикальность (допуск 1 мм)
                if abs(start.x - end.x) < 1.0:
                    x = start.x
                    y_min = min(start.y, end.y)
                    y_max = max(start.y, end.y)
                    height = y_max - y_min
                    
                    # Игнорируем слишком короткие линии (менее 50 мм) - это могут быть засечки
                    if height > 50:
                        x_coords.add(round(x, 1))
                        print(f"    Найдена: X={x:.1f}, высота={height:.1f}")
        
        return sorted(x_coords)

    def _extend_pattern_to_full_width(self, existing_points: List[float]) -> List[float]:
        """
        Дополняет паттерн линий до полной ширины двери
        Сохраняет ВСЕ существующие линии и добавляет новые только там, где их нет
        """
        if len(existing_points) < 2:
            # Если только одна линия или меньше, не добавляем новых
            return sorted(existing_points)
        
        sorted_points = sorted(existing_points)
        
        # Вычисляем шаг между соседними линиями
        distances = []
        for i in range(1, len(sorted_points)):
            dist = sorted_points[i] - sorted_points[i-1]
            # Игнорируем аномалии (разрывы больше 50 мм от среднего)
            if dist < 100:
                distances.append(dist)
        
        if not distances:
            return sorted_points
        
        # Берем медианный шаг
        distances.sort()
        step = distances[len(distances) // 2]
        
        print(f"    Шаг: {step:.1f} мм")
        
        # Берем существующие линии
        all_points = set(sorted_points)
        
        # Для каждого интервала между линиями проверяем, нет ли пропущенных линий
        for i in range(len(sorted_points) - 1):
            current_x = sorted_points[i]
            next_x = sorted_points[i + 1]
            
            # Добавляем промежуточные линии, если расстояние больше шага
            x = current_x + step
            while x < next_x - step/2:  # Оставляем небольшой допуск
                all_points.add(round(x, 1))
                print(f"      Добавлена промежуточная: X={x:.1f}")
                x += step
        
        # Продолжаем влево
        leftmost = sorted_points[0]
        x = leftmost - step
        while x >= self.min_x - 5:
            # Проверяем, нет ли уже такой линии
            if not any(abs(x - existing) < 2 for existing in all_points):
                all_points.add(round(x, 1))
                print(f"      Добавлена влево: X={x:.1f}")
            x -= step
        
        # Продолжаем вправо
        rightmost = sorted_points[-1]
        x = rightmost + step
        while x <= self.max_x + 5:
            if not any(abs(x - existing) < 2 for existing in all_points):
                all_points.add(round(x, 1))
                print(f"      Добавлена вправо: X={x:.1f}")
            x += step
        
        return sorted(all_points)
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
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    
    # Путь к существующему DXF файлу
    test_file = Path('/home/alex/NEW_NST_SERVER/TEST/door_dxf_out.dxf')
    
    if not test_file.exists():
        print(f"❌ Файл не найден: {test_file}")
        sys.exit(1)
    
    # Тестовые данные
    test_data = {
        'model': 'DELTA PRO MP',
        '09_Монтаж': 'НАКЛ',
        '01_Ширина': 1000,
        '02_Высота': 2200,
        '03_Петли': 'R',
        'vff': 300,
        'zff': 85,
        'pff': 85,
        'ff_pic': "L1",
        'options': [],
        '05_Лицо (рисунок)': 'CBR-S12',
        'head': False,
        'height_head': 0
    }
    
    try:
        # Загружаем документ
        print(f"\n📂 Загрузка файла: {test_file}")
        doc = DXFDocument(test_file)
        
        # Получаем границы ДО
        bounds_before = doc.get_bounds()
        print(f"\n📊 ДО добавления обналички:")
        print(f"   Границы: x=[{bounds_before[2]:.1f}, {bounds_before[0]:.1f}], "
              f"y=[{bounds_before[3]:.1f}, {bounds_before[1]:.1f}]")
        
        # Добавляем обналичку
        print(f"\n🔨 Добавление обналички...")
        ff = AddFFOut(test_data, doc)
        
        # Получаем границы ПОСЛЕ
        bounds_after = doc.get_bounds()
        print(f"\n📊 ПОСЛЕ добавления обналички:")
        print(f"   Границы: x=[{bounds_after[2]:.1f}, {bounds_after[0]:.1f}], "
              f"y=[{bounds_after[3]:.1f}, {bounds_after[1]:.1f}]")
        print(f"   finish_up_size = {ff.finish_up_size:.1f}")
        
        # Сохраняем результат
        output_file = test_file.parent / "door_dxf_out_with_ff.dxf"
        doc.save(output_file)
        print(f"\n✅ Результат сохранен: {output_file}")
        
        print("\n" + "="*60)
        print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
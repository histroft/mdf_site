"""
Модуль для создания DXF чертежа панели (рисунок + текст)
"""
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from shutil import copy
import sys
import os

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from make_order.dxf_modules.base import DXFDocument
from make_order.dxf_modules.inserting import insert_dxf
from make_order.dxf_modules.dxf_to_image import dxf_to_jpg
from make_order.dxf_modules.png_to_pdf import png_to_pdf

# Импортируем функцию add_watermark правильно
try:
    from make_order.dxf_modules.add_watermark import add_watermark
    HAS_WATERMARK = True
except ImportError:
    HAS_WATERMARK = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Модуль add_watermark не найден, водяные знаки не будут добавлены")

logger = logging.getLogger(__name__)


class MakePanelDXF:
    """
    Класс для создания DXF чертежа панели (только рисунок и текст)
    """
    
    # Константы
    BASE_WIDTH = 950
    BASE_HEIGHT = 2050
    PIC_BASE_WIDTH = 820
    PIC_OFFSET = 0  # Смещение для вставки рисунка (0 - начало координат)
    
    # Позиция текста (под рисунком, слева)
    TEXT_X = 0  # Начало координат по X (левая граница)
    TEXT_START_Y = -50  # Начальная Y позиция текста (под рисунком)
    TEXT_STEP = 50  # Шаг между строками
    
    # Пути к ресурсам
    PIC_DIR = "Pic"
    
    def __init__(self, data: Dict[str, Any]):
        """
        Args:
            data: словарь с данными заказа
        """
        self.data = data
        
        # Создаем уникальный ID заказа
        now = datetime.datetime.now()
        self.contract_ID = str(now.strftime("%d%m%Y%H%M%S"))
        
        # Создаем папку для заказа
        base_orders_dir = Path(__file__).parent.parent / 'orders'
        base_orders_dir.mkdir(exist_ok=True)
        
        self.path_to_order = base_orders_dir / self.contract_ID
        self.path_to_order.mkdir(parents=True, exist_ok=True)
        
        # Имена файлов
        self.out_file = self.path_to_order / "main.dxf"
        self.png_file = self.path_to_order / "main.png"
        self.pdf_file = self.path_to_order / "main.pdf"
        
        # Определяем, какой рисунок использовать
        self._determine_picture()
        
        # Извлекаем данные
        self._extract_data()
        
        # Настройка путей
        self._setup_paths()
        
        # Состояние
        self.doc: Optional[DXFDocument] = None
    
    def _determine_picture(self):
        """
        Определяет, какой рисунок использовать:
        - если наружный рисунок есть, используем его
        - если внутренний рисунок есть, используем его
        """
        out_pic = self.data.get('05_Лицо (рисунок)', '')
        in_pic = self.data.get('07_Внутр. отделка (рисунок)', '')
        
        if out_pic and out_pic != '-':
            self.pic = out_pic
            self.side = 'out'
            logger.info(f"   Используется наружный рисунок: {self.pic}")
        elif in_pic and in_pic != '-':
            self.pic = in_pic
            self.side = 'in'
            logger.info(f"   Используется внутренний рисунок: {self.pic}")
        else:
            self.pic = None
            logger.warning("   ⚠️ Рисунок не указан!")
    
    def _extract_data(self):
        """Извлекает данные из словаря"""
        self.width = int(self.data.get('01_Ширина', 0))
        self.height = int(self.data.get('02_Высота', 0))
        self.model = self.data.get('model', '')
        self.cost = float(self.data.get('cost', 0))
        
        logger.debug(f"   Размеры: {self.width}x{self.height}")
        logger.debug(f"   Модель: {self.model}")
        logger.debug(f"   Цена: {self.cost:.2f} руб.")
    
    def _setup_paths(self):
        """Настройка путей к файлам"""
        self.abs_path = Path(__file__).parent
        
        # Путь к базовому файлу (пустой шаблон)
        self.base_file = self.abs_path / 'DXF' / 'panel_base.dxf'
        
        # Если базового файла нет, создаем временный
        if not self.base_file.exists():
            self._create_base_file()
        
        # Путь к файлу рисунка
        self.pic_file = self._get_pic_file_path()
    
    def _create_base_file(self):
        """
        Создает базовый DXF файл (пустой чертеж)
        """
        logger.info("   📄 Создание базового файла panel_base.dxf")
        
        import ezdxf
        doc = ezdxf.new(dxfversion='AC1024') # type: ignore
        msp = doc.modelspace()
        
        # Создаем слой для текста
        if "TEXT_LAYER" not in doc.layers:
            doc.layers.new(name="TEXT_LAYER", dxfattribs={'color': 7})
        
        # Сохраняем
        doc.saveas(str(self.base_file))
        logger.debug(f"   ✅ Базовый файл создан: {self.base_file}")
    
    def _get_pic_file_path(self) -> Optional[Path]:
        """Определяет путь к файлу рисунка"""
        if not self.pic:
            return None
        
        pic_dir = self.abs_path / self.PIC_DIR
        
        # Специальные случаи
        if self.pic.startswith("S11"):
            if self.side == 'out':
                return pic_dir / 'S11_out.dxf'
            else:
                return pic_dir / 'S11_in.dxf'
        
        if self.pic.startswith("S12"):
            if self.side == 'out':
                return pic_dir / 'S12_out.dxf'
            else:
                return pic_dir / 'S12_in.dxf'
        
        if self.pic.startswith("НСТ_16_"):
            pic_name = self.pic.replace('НСТ_16_', '')
            if self.side == 'out':
                return pic_dir / f'{pic_name}_out.dxf'
            else:
                return pic_dir / f'{pic_name}_in.dxf'
        
        # Унифицированные файлы
        union_files = ['S4', 'S11', 'S12', 'Eve', 'Rhombus', 'River', 
                       'Slice', 'Stripe', 'S1', 'S2', 'Batista']
        for file_name in union_files:
            if file_name in self.pic:
                if self.side == 'out':
                    return pic_dir / f'{file_name}_out.dxf'
                else:
                    return pic_dir / f'{file_name}_in.dxf'
        
        # По умолчанию
        if self.side == 'out':
            return pic_dir / f'{self.pic}_out.dxf'
        else:
            return pic_dir / f'{self.pic}_in.dxf'
    
    def _prepare_base_file(self):
        """Копирует базовый файл и создает документ"""
        if not self.base_file.exists():
            error_msg = f'Базовый файл не найден: {self.base_file}'
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        copy(str(self.base_file), str(self.out_file))
        logger.debug(f"   Базовый файл скопирован: {self.base_file}")
        
        self.doc = DXFDocument(self.out_file)
    
    def build(self):
        """Основной метод построения чертежа панели"""
        logger.info("🏗️ Начало построения чертежа панели")
        
        # ШАГ 1: Подготовка базового файла
        self._prepare_base_file()
        
        # ШАГ 2: Вставка рисунка
        self._insert_picture()
        
        # ШАГ 3: Масштабирование
        self._scale()
        
        # ШАГ 4: Добавление текста
        self._add_text()
        
        # ШАГ 5: Делаем всё черным
        self._make_all_black()
        
        logger.info(f"✅ Построение панели завершено")
   
    
    def _insert_picture(self):
        """Вставляет рисунок на панель"""
        if not self.pic or not self.pic_file or not self.pic_file.exists():
            logger.warning(f"   ⚠️ Файл рисунка не найден: {self.pic_file}")
            return
        
        offset = (self.PIC_OFFSET, 0, 0)
        
        logger.info(f"   🖼️ Вставка рисунка: {self.pic_file.name}")
        
        success = insert_dxf(self.doc.msp, str(self.pic_file), offset)  # type: ignore
        
        if success:
            logger.info(f"   ✅ Рисунок вставлен")
        else:
            logger.error(f"   ❌ Ошибка вставки рисунка")
    
    def _scale(self):
        """Масштабирует чертеж под заданные размеры"""
        x_scale = self.width / self.BASE_WIDTH
        y_scale = self.height / self.BASE_HEIGHT
        
        logger.debug(f"   📏 Масштабирование: x={x_scale:.3f}, y={y_scale:.3f}")
        self.doc.scale(x_scale, y_scale) # type: ignore
    
    def _add_text(self):
        """Добавляет текстовую информацию на панель (слева под рисунком)"""
        logger.info("   📝 Добавление текста")
        
        # Определяем позицию текста (слева, под рисунком)
        x = self.TEXT_X
        y = self.TEXT_START_Y
        
        # Текст с информацией о панели
        text_lines = [
            f"Рисунок: {self.pic}",
            f"Размер: {self.width} x {self.height} мм",
            f"Модель: {self.model}",
            f"ID заказа: {self.contract_ID}",
            f"Цена: {self.cost:.2f} руб."  # Добавляем цену
        ]
        
        # Добавляем каждую строку
        for line in text_lines:
            if line:
                self.doc.add_text(  # type: ignore
                    line,
                    x, y,
                    height=40,
                    color=1,
                    layer="TEXT_LAYER"
                )
                y -= self.TEXT_STEP
        
        logger.debug(f"   ✅ Добавлено {len(text_lines)} строк текста")
    
    def _make_all_black(self):
        """Делает все линии черными"""
        changed = 0
        for entity in self.doc.msp:  # type: ignore
            if entity.dxf.get('color', 7) != 1:
                entity.dxf.color = 1
                changed += 1
        logger.debug(f"   ⚫ Изменено цветов: {changed}")
    
    def save(self):
        """Сохраняет документ"""
        if self.doc:
            self.doc.save()
            logger.debug(f"💾 Документ сохранен: {self.out_file}")
    
    def get_document(self) -> Optional[DXFDocument]:
        """Возвращает документ"""
        return self.doc
    
    def create_png(self, dpi: int = 200) -> Optional[Path]:
        """
        Конвертирует DXF в PNG
        
        Args:
            dpi: разрешение PNG
        
        Returns:
            Path: путь к PNG файлу или None при ошибке
        """
        logger.info("🖼️ Конвертация DXF в PNG")
        
        png_path = dxf_to_jpg(
            str(self.out_file),
            str(self.png_file),
            dpi=dpi
        )
        
        if png_path and os.path.exists(png_path):
            logger.info(f"   ✅ PNG создан: {png_path}")
            return Path(png_path)
        else:
            logger.error("   ❌ Ошибка создания PNG")
            return None
    
    def create_pdf(self, dpi: int = 200, add_watermark_flag: bool = True) -> Optional[Path]:
        """
        Конвертирует DXF в PDF (через PNG)
        
        Args:
            dpi: разрешение для промежуточного PNG
            add_watermark_flag: добавлять ли водяной знак
        
        Returns:
            Path: путь к PDF файлу или None при ошибке
        """
        logger.info("📄 Конвертация DXF в PDF")
        
        # ШАГ 1: Создаем PNG
        png_path = self.create_png(dpi=dpi)
        if not png_path:
            return None
        
        # ШАГ 2: Конвертируем PNG в PDF
        success = png_to_pdf(png_path, self.pdf_file)
        
        if not success:
            logger.error("   ❌ Ошибка создания PDF")
            return None
        
        # ШАГ 3: Добавляем водяной знак
        if add_watermark_flag and HAS_WATERMARK:
            success = add_watermark(
                self.pdf_file,
                self.pdf_file,
                watermark_text="TOREX",
                opacity=0.2,
                font_size=40,
                spacing=200,
                angle=45
            )
            if success:
                logger.info(f"   ✅ Водяной знак добавлен")
        elif add_watermark_flag and not HAS_WATERMARK:
            logger.warning("   ⚠️ Модуль водяных знаков не доступен")
        
        logger.info(f"   ✅ PDF создан: {self.pdf_file}")
        return self.pdf_file
    
    def build_all(self, dpi: int = 200, add_watermark_flag: bool = True) -> str:
        """
        Полный цикл создания: DXF -> PNG -> PDF
        
        Args:
            dpi: разрешение для PNG
            add_watermark_flag: добавлять ли водяной знак
        
        Returns:
            Dict: словарь с путями к созданным файлам
        """
        logger.info("🚀 ЗАПУСК ПОЛНОГО ЦИКЛА СОЗДАНИЯ ПАНЕЛИ")
        
        # ШАГ 1: Создаем DXF
        self.build()
        self.save()
        
        # ШАГ 2: Создаем PNG
        png_path = self.create_png(dpi=dpi)
        
        # ШАГ 3: Создаем PDF
        pdf_path = None
        if png_path:
            pdf_path = self.create_pdf(dpi=dpi, add_watermark_flag=add_watermark_flag)
        
        return self.contract_ID

# =============================================================================
# ТЕСТОВЫЙ ЗАПУСК
# =============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🧪 ТЕСТОВЫЙ ЗАПУСК MakePanelDXF")
    print("="*60)
    
    # Тестовые данные
    test_data = {
        'model': 'DELTA PRO MP',
        '01_Ширина': 1200,
        '02_Высота': 2200,
        '03_Петли': 'R',
        '05_Лицо (рисунок)': 'Castle',
        '07_Внутр. отделка (рисунок)': '-',
        'cost': 15000.00
    }
    
    print(f"\n📋 Тестовые данные:")
    for key, value in test_data.items():
        print(f"   {key}: {value}")
    
    try:
        # Создаем панель
        print(f"\n🔨 Создание панели...")
        panel = MakePanelDXF(test_data)
        
        # Полный цикл создания
        files = panel.build_all(dpi=200, add_watermark_flag=True)
        
        print(f"\n✅ Панель создана:")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
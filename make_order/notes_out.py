"""
Модуль для добавления аннотаций на чертеж наружной двери
"""
import logging
from typing import Dict, Any, List
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"📁 Добавлен путь: {project_root}")

from make_order.dxf_modules.base import DXFDocument

logger = logging.getLogger(__name__)


def add_annotations_out(data: Dict[str, Any], doc: DXFDocument):
    """
    Добавляет аннотации на чертеж наружной двери
    
    Args:
        data: словарь с данными заказа
        doc: открытый DXF документ
    """
    logger.info("📝 Добавление аннотаций")
    
    # Получаем границы чертежа
    max_x, max_y, min_x, min_y = doc.get_bounds()
    center_x = (min_x + max_x) / 2
    
    # 1. Надпись "Вид снаружи"
    doc.add_text(
        "ВИД СНАРУЖИ",
        center_x - 150,
        max_y + 50,
        height=40,
        color=1,
        layer="TEXT_LAYER"
    )
    
    # 2. Надпись разреза А-А (вертикальный разрез)
    # Размещаем справа от чертежа
    doc.add_text(
        "А",
        min_x + 200,
        max_y +50,
        height=40,
        color=1,
        layer="TEXT_LAYER"
    )
    
    doc.add_text(
        "А",
        min_x + 200,
        min_y -50,
        height=40,
        color=1,
        layer="TEXT_LAYER"
    )
    
    # Линия разреза А-А
    doc.add_line(
        min_x + 170, max_y,
        min_x + 170, max_y +60,
        color=1,
        layer="LINE_LAYER"
    )
    doc.add_line(
        min_x + 170, min_y,
        min_x + 170, min_y -60,
        color=1,
        layer="LINE_LAYER"
    )
    
    
    # 3. Надпись разреза Б-Б (горизонтальный разрез)
    # Размещаем снизу от чертежа
    doc.add_text(
        "Б",
        min_x -40,
        min_y +400,
        height=40,
        color=1,
        layer="TEXT_LAYER"
    )
    
    doc.add_text(
        "Б",
        max_x +40,
        min_y +400,
        height=40,
        color=1,
        layer="TEXT_LAYER"
    )
    
    # Линия разреза Б-Б
    doc.add_line(
        min_x, min_y +360,
        min_x-60, min_y +360,
        color=1,
        layer="LINE_LAYER"
    )
    doc.add_line(
        max_x, min_y +360,
        max_x+60, min_y +360,
        color=1,
        layer="LINE_LAYER"
    )
    

    logger.info("✅ Аннотации добавлены")
    
    
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
    print("🧪 ТЕСТОВЫЙ ЗАПУСК AddNotesOut")
    print("="*60)
    
    # Путь к существующему DXF файлу
    test_file = Path('/home/alex/NEW_NST_SERVER/TEST/door_dxf_out_with_ff.dxf')
    
    if not test_file.exists():
        print(f"❌ Файл не найден: {test_file}")
        sys.exit(1)
    
    # Тестовые данные
    test_data = {
        'model': 'DELTA PRO MP',
        '01_Ширина': '1200',
        '02_Высота': '2200',
        '03_Петли': 'R',
        '09_Монтаж': 'НАКЛ',
        '04_Лицо (цвет)': 'Белый',
        '05_Лицо (рисунок)': 'Busoni',
        '06_Внутр. отделка (цвет)': 'Белый',
        '07_Внутр. отделка (рисунок)': 'Castle',
        '08_Фурнитура': 'ХКР_БН МОН_ALFA',
        '10_Обналичка': 'Наличник',
        'options': ['Опция 1', 'Опция 2'],
        'TDOT': '12345',
        'manager': 'Иванов',
        'date': '18.03.2026'
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
        
        # Добавляем аннотации
        print(f"\n🔨 Добавление аннотаций...")
        add_annotations_out(test_data, doc)
        
        # Показываем границы ПОСЛЕ
        bounds_after = doc.get_bounds()
        print(f"\n📊 Границы ПОСЛЕ:")
        print(f"   x=[{bounds_after[2]:.1f}, {bounds_after[0]:.1f}]")
        print(f"   y=[{bounds_after[3]:.1f}, {bounds_after[1]:.1f}]")
        
        # Сохраняем результат
        output_file = test_file.parent / "door_dxf_out_with_notes.dxf"
        doc.save(output_file)
        print(f"\n✅ Результат сохранен: {output_file}")
        
        print("\n" + "="*60)
        print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
"""
Модуль для добавления аннотаций на чертеж внутренней двери
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from make_order.dxf_modules.base import DXFDocument

logger = logging.getLogger(__name__)


def add_annotations_in(data: Dict[str, Any], doc: DXFDocument):
    """
    Добавляет аннотации на чертеж внутренней двери
    
    Args:
        data: словарь с данными заказа
        doc: открытый DXF документ
    """
    logger.info("📝 Добавление аннотаций на внутренний вид")
    
    # Получаем границы чертежа
    max_x, max_y, min_x, min_y = doc.get_bounds()
    center_x = (min_x + max_x) / 2
    
    # 1. Надпись "Вид изнутри" вверху по центру
    doc.msp.add_text( # type: ignore
        "ВИД ИЗНУТРИ",
        dxfattribs={
            'height': 40,
            'insert': (center_x - 150, max_y + 50, 0),
            'color': 1,
            'layer': "TEXT_LAYER"
        }
    )
    
    # # 2. Габаритный размер по ширине (внизу)
    # y_dim = min_y - 50
    
    # # Выносные линии
    # doc.msp.add_line( # type: ignore
    #     (min_x, y_dim - 10),
    #     (min_x, y_dim + 10),
    #     dxfattribs={'color': 3}
    # )
    # doc.msp.add_line( # type: ignore
    #     (max_x, y_dim - 10),
    #     (max_x, y_dim + 10),
    #     dxfattribs={'color': 3}
    # )
    
    # # Размерная линия
    # doc.msp.add_line( # type: ignore
    #     (min_x, y_dim),
    #     (max_x, y_dim),
    #     dxfattribs={'color': 3}
    # )
    
    # # Текст размера
    # doc.msp.add_text( # type: ignore
    #     f"{data.get('01_Ширина', 0)}",
    #     dxfattribs={
    #         'height': 25,
    #         'insert': (center_x, y_dim + 20, 0),
    #         'color': 3,
    #         'layer': "TEXT_LAYER"
    #     }
    # )
    
    # # 3. Габаритный размер по высоте (слева)
    # x_dim = min_x - 80
    
    # # Выносные линии
    # doc.msp.add_line( # type: ignore
    #     (x_dim - 10, min_y),
    #     (x_dim + 10, min_y),
    #     dxfattribs={'color': 3}
    # )
    # doc.msp.add_line( # type: ignore
    #     (x_dim - 10, max_y),
    #     (x_dim + 10, max_y),
    #     dxfattribs={'color': 3}
    # )
    
    # # Размерная линия
    # doc.msp.add_line( # type: ignore
    #     (x_dim, min_y),
    #     (x_dim, max_y),
    #     dxfattribs={'color': 3}
    # )
    
    # # Текст размера
    # doc.msp.add_text( # type: ignore
    #     f"{data.get('02_Высота', 0)}",
    #     dxfattribs={
    #         'height': 25,
    #         'insert': (x_dim - 40, (min_y + max_y) / 2, 0),
    #         'color': 3,
    #         'layer': "TEXT_LAYER"
    #     }
    # )
    
    logger.info("✅ Аннотации на внутренний вид добавлены")


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
    print("🧪 ТЕСТОВЫЙ ЗАПУСК AddNotesIn")
    print("="*60)
    
    # Путь к существующему DXF файлу
    test_file = Path('/home/alex/NEW_NST_SERVER/TEST/door_dxf_in_with_ff.dxf')
    
    if not test_file.exists():
        print(f"❌ Файл не найден: {test_file}")
        print("Сначала создайте файл через in_dxf.py")
        sys.exit(1)
    
    # Тестовые данные
    test_data = {
        '01_Ширина': '1200',
        '02_Высота': '2200'
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
        add_annotations_in(test_data, doc)
        
        # Показываем границы ПОСЛЕ
        bounds_after = doc.get_bounds()
        print(f"\n📊 Границы ПОСЛЕ:")
        print(f"   x=[{bounds_after[2]:.1f}, {bounds_after[0]:.1f}]")
        print(f"   y=[{bounds_after[3]:.1f}, {bounds_after[1]:.1f}]")
        
        # Сохраняем результат
        output_file = test_file.parent / "door_dxf_in_with_notes.dxf"
        doc.save(output_file)
        print(f"\n✅ Результат сохранен: {output_file}")
        
        print("\n" + "="*60)
        print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
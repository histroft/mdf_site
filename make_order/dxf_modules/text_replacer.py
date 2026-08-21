import ezdxf
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class TextReplacer:
    """
    Класс для замены текста в DXF файле.
    Открывает файл один раз и выполняет множество замен.
    """
    
    def __init__(self, dxf_file: str):
        """
        Args:
            dxf_file: путь к DXF файлу
        """
        self.dxf_file = Path(dxf_file)
        self.doc = None
        self.replacements = {}  # Словарь {старый_текст: новый_текст}
        self.stats = {'TEXT': 0, 'MTEXT': 0, 'TOTAL': 0}
        
        # Загружаем файл
        self._load()
    
    def _load(self):
        """Загружает DXF файл"""
        if not self.dxf_file.exists():
            raise FileNotFoundError(f"Файл не найден: {self.dxf_file}")
        
        self.doc = ezdxf.readfile(str(self.dxf_file))
        logger.info(f"📄 Загружен файл: {self.dxf_file}")
    
    def add_replacement(self, old_text: str, new_text: str):
        """
        Добавляет пару для замены
        
        Args:
            old_text: текст для поиска
            new_text: текст для замены
        """
        if old_text and old_text.strip():
            self.replacements[old_text] = new_text
            logger.debug(f"   Добавлена замена: '{old_text}' -> '{new_text}'")
    
    def add_replacements(self, replacements: Dict[str, str]):
        """
        Добавляет несколько замен
        
        Args:
            replacements: словарь {старый_текст: новый_текст}
        """
        for old, new in replacements.items():
            self.add_replacement(old, new)
    
    def process(self, save_file: str = None) -> Dict[str, int]:
        """
        Выполняет все замены и сохраняет файл
        
        Args:
            save_file: путь для сохранения (если None, сохраняет в исходный файл)
        
        Returns:
            Dict со статистикой замен
        """
        if not self.replacements:
            logger.warning("⚠️ Нет замен для выполнения")
            return self.stats
        
        logger.info(f"🔍 Выполнение {len(self.replacements)} замен:")
        for old, new in self.replacements.items():
            logger.info(f"   '{old}' -> '{new}'")
        
        # Заменяем в пространстве модели
        self._process_entities(self.doc.modelspace())
        
        # Заменяем в блоках
        for block in self.doc.blocks:
            if block.name != '*Model_Space':
                self._process_entities(block)
        
        # Сохраняем результат
        output_file = Path(save_file) if save_file else self.dxf_file
        self.doc.saveas(str(output_file))
        
        logger.info(f"💾 Файл сохранен: {output_file}")
        logger.info(f"📊 Статистика: TEXT={self.stats['TEXT']}, MTEXT={self.stats['MTEXT']}, Всего={self.stats['TOTAL']}")
        
        return self.stats
    
    def _process_entities(self, layout):
        """
        Обрабатывает все сущности в layout
        """
        for entity in layout:
            etype = entity.dxftype()
            
            if etype == 'TEXT':
                self._process_text_entity(entity)
            elif etype == 'MTEXT':
                self._process_mtext_entity(entity)
    
    def _process_text_entity(self, entity):
        """
        Обрабатывает текстовую сущность
        """
        original_text = entity.dxf.text
        new_text = original_text
        
        # Применяем все замены
        for old, new in self.replacements.items():
            if old in new_text:
                new_text = new_text.replace(old, new)
        
        # Если текст изменился, обновляем
        if new_text != original_text:
            entity.dxf.text = new_text
            self.stats['TEXT'] += 1
            self.stats['TOTAL'] += 1
            logger.debug(f"      TEXT: '{original_text}' -> '{new_text}'")
    
    def _process_mtext_entity(self, entity):
        """
        Обрабатывает MTEXT сущность
        """
        original_text = entity.dxf.text
        new_text = original_text
        
        # Применяем все замены
        for old, new in self.replacements.items():
            if old in new_text:
                new_text = new_text.replace(old, new)
        
        # Если текст изменился, обновляем
        if new_text != original_text:
            entity.dxf.text = new_text
            self.stats['MTEXT'] += 1
            self.stats['TOTAL'] += 1
            logger.debug(f"      MTEXT: '{original_text[:30]}...' -> '{new_text[:30]}...'")


def quick_replace_text(dxf_file: str, replacements: Dict[str, str], save_file: str = None) -> Dict[str, int]:
    """
    Быстрая замена текста в DXF файле (упрощенная функция)
    
    Args:
        dxf_file: путь к DXF файлу
        replacements: словарь {старый_текст: новый_текст}
        save_file: путь для сохранения (если None, сохраняет в исходный файл)
    
    Returns:
        Dict со статистикой замен
    """
    replacer = TextReplacer(dxf_file)
    replacer.add_replacements(replacements)
    return replacer.process(save_file)


# Пример использования в вашем коде:
def replace_cut_text(self):
    """
    Заменяет текст в разрезах на актуальные размеры
    """
    logger.info("📝 Замена текста в разрезах")
    
    w1, h2 = self.calc_spec_size()
    
    # Для вертикального разреза
    replacer_vert = TextReplacer(self.vert_cut_file)
    replacer_vert.add_replacements({
        'WIDTH 0': str(self.data['01_Ширина']),
        'vff': str(self.data['vff']),
        'zff': str(self.data['zff']),
        'pff': str(self.data['pff']),
        'H0': str(self.data['02_Высота']),
        'WIDTH 1': str(w1),
        'H2': str(h2),
        'HEAD': str(self.data['height_head'])
    })
    replacer_vert.process(self.vert_cut_file)
    
    # Для горизонтального разреза
    replacer_horiz = TextReplacer(self.horiz_cut_file)
    replacer_horiz.add_replacements({
        'WIDTH 0': str(self.data['01_Ширина']),
        'vff': str(self.data['vff']),
        'zff': str(self.data['zff']),
        'pff': str(self.data['pff']),
        'H0': str(self.data['02_Высота']),
        'WIDTH 1': str(w1),
        'H2': str(h2)
    })
    replacer_horiz.process(self.horiz_cut_file)


# ИЛИ еще проще - одна функция для всех замен:
def replace_all_cut_text(self):
    """
    Заменяет текст во всех разрезах за один проход
    """
    logger.info("📝 Замена текста в разрезах")
    
    w1, h2 = self.calc_spec_size()
    
    # Общие замены для обоих разрезов
    common_replacements = {
        'WIDTH 0': str(self.data['01_Ширина']),
        'vff': str(self.data['vff']),
        'zff': str(self.data['zff']),
        'pff': str(self.data['pff']),
        'H0': str(self.data['02_Высота']),
        'WIDTH 1': str(w1),
        'H2': str(h2)
    }
    
    # Вертикальный разрез (дополнительно HEAD)
    vert_replacements = common_replacements.copy()
    vert_replacements['HEAD'] = str(self.data['height_head'])
    
    # Применяем замены
    quick_replace_text(self.vert_cut_file, vert_replacements, self.vert_cut_file)
    quick_replace_text(self.horiz_cut_file, common_replacements, self.horiz_cut_file)


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Пример использования
    test_file = "/home/alex/TEST_SERVER/TEST_DXF/door_dxf_out.dxf"
    
    # Способ 1: Через класс
    replacer = TextReplacer(test_file)
    replacer.add_replacement('WIDTH 0', '1000')
    replacer.add_replacement('H0', '2200')
    replacer.add_replacement('vff', '85')
    stats = replacer.process()
    
    # Способ 2: Через упрощенную функцию
    replacements = {
        'WIDTH 0': '1000',
        'H0': '2200',
        'vff': '85',
        'zff': '85',
        'pff': '85'
    }
    stats = quick_replace_text(test_file, replacements)
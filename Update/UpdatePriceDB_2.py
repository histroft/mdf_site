"""
Оптимизированный парсер XML в SQLite с поддержкой потоковой обработки,
транзакций и массовых вставок.
"""

import sys
import logging
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator
from contextlib import contextmanager
from datetime import datetime

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_parser.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SQL константы
CREATE_TABLES_SQL = {
    'base_prices': '''
        CREATE TABLE IF NOT EXISTS BasePrices (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Registrar TEXT,
            RowNumber INTEGER DEFAULT 0,
            PriceType TEXT NOT NULL,
            Nomenclature TEXT NOT NULL,
            Currency TEXT DEFAULT 'RUB',
            Price REAL DEFAULT 0.0,
            Unit TEXT DEFAULT 'шт',
            DiscountPercent REAL DEFAULT 0.0,
            PriceCalcMethod TEXT,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            LastUpdated TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(Nomenclature, PriceType, RowNumber)
        )
    ''',
    'additional_options': '''
        CREATE TABLE IF NOT EXISTS AdditionalOptions (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            OptionID TEXT,
            Nomenclature TEXT,
            Registrar TEXT,
            RowNumber INTEGER DEFAULT 0,
            Name TEXT,
            IsPercentOfBasePrice BOOLEAN DEFAULT 0,
            PriceType TEXT,
            Price REAL DEFAULT 0.0,
            Currency TEXT DEFAULT 'RUB',
            Unit TEXT DEFAULT 'шт',
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            LastUpdated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    'option_conditions': '''
        CREATE TABLE IF NOT EXISTS OptionConditions (
            ConditionID INTEGER PRIMARY KEY AUTOINCREMENT,
            AdditionalOptionID INTEGER,
            ConditionName TEXT,
            ConditionLogicOR BOOLEAN DEFAULT 0,
            ConditionNot BOOLEAN DEFAULT 0,
            ConditionText TEXT,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (AdditionalOptionID) REFERENCES AdditionalOptions(ID) ON DELETE CASCADE
        )
    ''',
    'condition_properties': '''
        CREATE TABLE IF NOT EXISTS ConditionProperties (
            ConditionPropertyID INTEGER PRIMARY KEY AUTOINCREMENT,
            ConditionID INTEGER,
            PropertyName TEXT,
            Value TEXT,
            ComparisonType TEXT,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ConditionID) REFERENCES OptionConditions(ConditionID) ON DELETE CASCADE
        )
    '''
}

INDEXES_SQL = [
    'CREATE INDEX IF NOT EXISTS idx_base_prices_nom ON BasePrices (Nomenclature)',
    'CREATE INDEX IF NOT EXISTS idx_base_prices_type ON BasePrices (PriceType)',
    'CREATE INDEX IF NOT EXISTS idx_options_nom ON AdditionalOptions (Nomenclature)',
    'CREATE INDEX IF NOT EXISTS idx_options_id ON AdditionalOptions (OptionID)',
    'CREATE INDEX IF NOT EXISTS idx_conditions_opt ON OptionConditions (AdditionalOptionID)',
    'CREATE INDEX IF NOT EXISTS idx_properties_cond ON ConditionProperties (ConditionID)',
    'CREATE INDEX IF NOT EXISTS idx_base_prices_updated ON BasePrices (LastUpdated)'
]

INSERT_BASE_PRICE = '''
    INSERT OR REPLACE INTO BasePrices 
    (Registrar, RowNumber, PriceType, Nomenclature, Currency, 
     Price, Unit, DiscountPercent, PriceCalcMethod, LastUpdated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

INSERT_OPTION = '''
    INSERT OR REPLACE INTO AdditionalOptions 
    (OptionID, Nomenclature, Registrar, RowNumber, Name, 
     IsPercentOfBasePrice, PriceType, Price, LastUpdated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

INSERT_CONDITION = '''
    INSERT OR REPLACE INTO OptionConditions 
    (AdditionalOptionID, ConditionName, ConditionLogicOR, ConditionNot, ConditionText)
    VALUES (?, ?, ?, ?, ?)
'''

INSERT_PROPERTY = '''
    INSERT OR REPLACE INTO ConditionProperties 
    (ConditionID, PropertyName, Value, ComparisonType)
    VALUES (?, ?, ?, ?)
'''

DELETE_ALL_BASE_PRICES = 'DELETE FROM BasePrices'
DELETE_ALL_OPTIONS = 'DELETE FROM AdditionalOptions'


@contextmanager
def get_db_connection(db_path: str):
    """Контекстный менеджер для подключения к БД"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Улучшает производительность при конкурентном доступе
        conn.execute("PRAGMA synchronous = NORMAL")  # Баланс скорости и надёжности
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Ошибка БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


def parse_float(value_str: str) -> float:
    """Безопасное преобразование в float (без валидации знака)"""
    if not value_str or value_str.strip() == '':
        return 0.0
    try:
        # Замена запятой на точку и удаление пробелов
        cleaned = value_str.strip().replace(',', '.').replace(' ', '')
        return float(cleaned)
    except (ValueError, TypeError):
        logger.warning(f"Не удалось преобразовать '{value_str}' в число, используем 0")
        return 0.0


def parse_int(value_str: str) -> int:
    """Безопасное преобразование в int"""
    if not value_str or value_str.strip() == '':
        return 0
    try:
        return int(float(value_str.strip()))
    except (ValueError, TypeError):
        logger.warning(f"Не удалось преобразовать '{value_str}' в целое число, используем 0")
        return 0


def parse_bool(value_str: str) -> bool:
    """Безопасное преобразование в bool"""
    if not value_str:
        return False
    value_str = value_str.strip().lower()
    return value_str in ('true', '1', 'да', 'yes')


def create_tables(conn: sqlite3.Connection):
    """Создаёт таблицы и индексы"""
    cursor = conn.cursor()
    
    # Создаём таблицы
    for table_name, create_sql in CREATE_TABLES_SQL.items():
        cursor.execute(create_sql)
        logger.debug(f"Таблица {table_name} создана/проверена")
    
    # Создаём индексы
    for index_sql in INDEXES_SQL:
        cursor.execute(index_sql)
    
    conn.commit()
    logger.info("✅ Все таблицы и индексы созданы/проверены")


def parse_base_prices_streaming(xml_path: str, 
                                only_price_type: Optional[str] = None,
                                exclude_price_type: Optional[str] = None) -> Generator[Dict, None, None]:
    """
    Потоковый парсинг базовых цен из XML файла
    """
    if not Path(xml_path).exists():
        logger.warning(f"Файл не найден: {xml_path}")
        return
    
    try:
        context = ET.iterparse(xml_path, events=('end',))
        
        for event, elem in context:
            if elem.tag == 'Номенклатура':
                price_type = elem.attrib.get("ТипЦен", "")
                
                # Фильтрация
                if only_price_type and price_type != only_price_type:
                    elem.clear()
                    continue
                if exclude_price_type and price_type == exclude_price_type:
                    elem.clear()
                    continue
                
                # Получаем цену (может быть отрицательной - это скидка, не валидируем)
                price_value = parse_float(elem.attrib.get("Цена", "0"))
                discount_value = parse_float(elem.attrib.get("ПроцентСкидкиНаценки", "0"))
                
                price_data = {
                    'registrar': elem.attrib.get("Регистратор", ""),
                    'rownum': parse_int(elem.attrib.get("НомерСтроки", "0")),
                    'price_type': price_type,
                    'nomenclature': elem.attrib.get("Номенклатура", ""),
                    'currency': elem.attrib.get("Валюта", "RUB"),
                    'price': price_value,  # Цена может быть любой (в т.ч. отрицательной - это скидка)
                    'unit': elem.attrib.get("ЕдиницаИзмерения", "шт"),
                    'discount': discount_value,  # Скидка тоже может быть любой
                    'price_calc': elem.attrib.get("СпособРасчетаЦены", "")
                }
                
                # Валидируем только наличие обязательных полей
                if price_data['nomenclature'] and price_data['price_type']:
                    yield price_data
                
                elem.clear()
                
    except ET.ParseError as e:
        logger.error(f"Ошибка парсинга XML {xml_path}: {e}")
        raise


def parse_additional_options_streaming(xml_path: str) -> Generator[Dict, None, None]:
    """
    Потоковый парсинг дополнительных опций из XML файла
    
    Args:
        xml_path: путь к XML файлу
        
    Yields:
        словарь с данными об опции и её условиях
    """
    if not Path(xml_path).exists():
        logger.warning(f"Файл не найден: {xml_path}")
        return
    
    try:
        context = ET.iterparse(xml_path, events=('end',))
        
        for event, elem in context:
            if elem.tag == 'ДопОпция':
                option_data = {
                    'option_id': elem.attrib.get("КодОпции", ""),
                    'registrar': elem.attrib.get("Регистратор", ""),
                    'row_number': parse_int(elem.attrib.get("НомерСтроки", "0")),
                    'name': elem.attrib.get("НаименованиеОпции", ""),
                    'is_percent': parse_bool(elem.attrib.get("ПроцентОтБазовойЦены", "false")),
                    'nomenclature': elem.attrib.get("Номенклатура", ""),
                    'price_type': elem.attrib.get("ТипЦен", ""),
                    'price': parse_float(elem.attrib.get("Цена", "0")),
                    'conditions': []
                }
                
                if not option_data['option_id'] or not option_data['nomenclature']:
                    elem.clear()
                    continue
                
                # Парсим условия
                for condition in elem.findall("УсловияХарактеристики"):
                    cond_data = {
                        'name': condition.attrib.get("НаименованиеУсловия", ""),
                        'logic_or': parse_bool(condition.attrib.get("УсловиеИЛИ", "false")),
                        'not': parse_bool(condition.attrib.get("УсловиеНЕ", "false")),
                        'text': condition.attrib.get("УсловиеТЕКСТ", ""),
                        'properties': []
                    }
                    
                    # Парсим свойства условия
                    for cond_prop in condition.findall("ТЧУсловие"):
                        prop_data = {
                            'property_name': cond_prop.attrib.get("Свойство", ""),
                            'value': cond_prop.attrib.get("Значение", ""),
                            'comparison_type': cond_prop.attrib.get("ВидСравнения", "")
                        }
                        if prop_data['property_name'] and prop_data['value']:
                            cond_data['properties'].append(prop_data)
                    
                    if cond_data['name'] or cond_data['properties']:
                        option_data['conditions'].append(cond_data)
                
                yield option_data
                elem.clear()
                
    except ET.ParseError as e:
        logger.error(f"Ошибка парсинга XML {xml_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при парсинге {xml_path}: {e}")
        raise


def save_base_prices_batch(conn: sqlite3.Connection, 
                           prices: List[Dict], 
                           batch_size: int = 1000):
    """
    Пакетное сохранение базовых цен с использованием executemany
    
    Args:
        conn: подключение к БД
        prices: список словарей с ценами
        batch_size: размер пакета
    """
    cursor = conn.cursor()
    total = 0
    
    # Обрабатываем пакетами
    for i in range(0, len(prices), batch_size):
        batch = prices[i:i + batch_size]
        
        # Подготовка данных для пакетной вставки
        data = [
            (
                p['registrar'],
                p['rownum'],
                p['price_type'],
                p['nomenclature'],
                p['currency'],
                p['price'],
                p['unit'],
                p['discount'],
                p['price_calc'],
                datetime.now().isoformat()
            )
            for p in batch
        ]
        
        cursor.executemany(INSERT_BASE_PRICE, data)
        total += len(batch)
        
        if total % 5000 == 0:
            logger.info(f"   Сохранено базовых цен: {total}")
    
    conn.commit()
    return total


def save_options_with_conditions(conn: sqlite3.Connection, 
                                 options: List[Dict],
                                 batch_size: int = 500):
    """
    Пакетное сохранение опций и их условий с обработкой дубликатов
    """
    cursor = conn.cursor()
    option_count = 0
    
    for i in range(0, len(options), batch_size):
        batch = options[i:i + batch_size]
        
        for opt_data in batch:
            # Проверяем существование опции
            cursor.execute('''
                SELECT ID FROM AdditionalOptions 
                WHERE OptionID = ? AND Nomenclature = ? AND PriceType = ? AND RowNumber = ?
            ''', (opt_data['option_id'], opt_data['nomenclature'], 
                  opt_data['price_type'], opt_data['row_number']))
            
            row = cursor.fetchone()
            
            if row is None:
                # Опции нет - вставляем
                cursor.execute('''
                    INSERT INTO AdditionalOptions 
                    (OptionID, Nomenclature, Registrar, RowNumber, Name, 
                     IsPercentOfBasePrice, PriceType, Price, LastUpdated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (opt_data['option_id'], opt_data['nomenclature'],
                      opt_data['registrar'], opt_data['row_number'],
                      opt_data['name'], opt_data['is_percent'],
                      opt_data['price_type'], opt_data['price'],
                      datetime.now().isoformat()))
                additional_option_id = cursor.lastrowid
            else:
                # Опция уже есть - проверяем, совпадают ли условия
                existing_id = row[0]
                
                # Получаем существующие условия
                cursor.execute('''
                    SELECT cp.Value
                    FROM ConditionProperties cp
                    JOIN OptionConditions oc ON cp.ConditionID = oc.ConditionID
                    WHERE oc.AdditionalOptionID = ?
                ''', (existing_id,))
                
                existing_conditions = set([c[0] for c in cursor.fetchall()])
                
                # Получаем новые условия
                new_conditions = set()
                for cond in opt_data['conditions']:
                    for prop in cond['properties']:
                        new_conditions.add(prop['value'])
                
                if existing_conditions != new_conditions:
                    # Условия разные - создаём новую опцию с изменённым OptionID
                    new_option_id = f"{opt_data['option_id']}_{len(existing_conditions)}"
                    cursor.execute('''
                        INSERT INTO AdditionalOptions 
                        (OptionID, Nomenclature, Registrar, RowNumber, Name, 
                         IsPercentOfBasePrice, PriceType, Price, LastUpdated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (new_option_id, opt_data['nomenclature'],
                          opt_data['registrar'], opt_data['row_number'],
                          opt_data['name'], opt_data['is_percent'],
                          opt_data['price_type'], opt_data['price'],
                          datetime.now().isoformat()))
                    additional_option_id = cursor.lastrowid
                    logger.info(f"   Создан дубликат опции с новым ID: {new_option_id}")
                else:
                    # Условия совпадают - используем существующую
                    additional_option_id = existing_id
            
            # Удаляем старые условия для этой опции (если создали новую или обновляем)
            if row is None or existing_conditions != new_conditions:
                cursor.execute('''
                    DELETE FROM ConditionProperties 
                    WHERE ConditionID IN (SELECT ConditionID FROM OptionConditions WHERE AdditionalOptionID = ?)
                ''', (additional_option_id,))
                cursor.execute('DELETE FROM OptionConditions WHERE AdditionalOptionID = ?', (additional_option_id,))
            
            # Сохраняем новые условия
            for condition in opt_data['conditions']:
                cursor.execute('''
                    INSERT INTO OptionConditions 
                    (AdditionalOptionID, ConditionName, ConditionLogicOR, ConditionNot, ConditionText)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    additional_option_id,
                    condition['name'],
                    condition['logic_or'],
                    condition['not'],
                    condition['text']
                ))
                
                condition_id = cursor.lastrowid
                
                # Сохраняем свойства условия
                for prop in condition['properties']:
                    cursor.execute('''
                        INSERT INTO ConditionProperties 
                        (ConditionID, PropertyName, Value, ComparisonType)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        condition_id,
                        prop['property_name'],
                        prop['value'],
                        prop['comparison_type']
                    ))
            
            option_count += 1
            if option_count % 500 == 0:
                logger.info(f"   Обработано опций: {option_count}")
        
        # Commit после каждого пакета
        conn.commit()
    
    return option_count

def reset_database_completely(sqlite_db_path: str):
    """Полный сброс базы данных - удаляет все таблицы"""
    with get_db_connection(sqlite_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Получаем все таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
            logger.info(f"   Удалена таблица: {table[0]}")
        
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        logger.info("✅ База данных полностью сброшена")



def update_price_db_from_xml(base_price_xml_path: str, 
                            all_prices_xml_path: str, 
                            sqlite_db_path: str,
                            clear_existing: bool = True):
    """
    Оптимизированная загрузка данных из XML файлов в SQLite
    
    Args:
        base_price_xml_path: путь к XML с базовой ценой (только "Цены ТД ТОРЭКС")
        all_prices_xml_path: путь к XML со всеми ценами (кроме базовой + опции)
        sqlite_db_path: путь к БД SQLite
        clear_existing: очищать ли существующие данные перед вставкой
    """
    
    reset_database_completely(sqlite_db_path)
    
    logger.info("=" * 60)
    logger.info("ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ ЦЕН (оптимизированная версия)")
    logger.info("=" * 60)
    
    # Проверяем существование файлов
    if not Path(base_price_xml_path).exists():
        logger.error(f"Файл не найден: {base_price_xml_path}")
        return
    
    if not Path(all_prices_xml_path).exists():
        logger.error(f"Файл не найден: {all_prices_xml_path}")
        return
    
    # Создаём директорию для БД
    Path(sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection(sqlite_db_path) as conn:
        # Создаём таблицы
        create_tables(conn)
        
        # Очищаем существующие данные, если нужно
        if clear_existing:
            logger.info("🧹 Очистка существующих данных...")
            cursor = conn.cursor()
            cursor.execute(DELETE_ALL_BASE_PRICES)
            cursor.execute(DELETE_ALL_OPTIONS)
            conn.commit()
            logger.info("   Данные очищены")
        
        # ==================== 1. БАЗОВЫЕ ЦЕНЫ ====================
        logger.info("\n📊 Обработка базовых цен...")
        
        # Собираем все базовые цены в список (можно и дальше потоково, но для простоты оставим список)
        base_prices = []
        
        # 1.1. Базовая цена из первого файла (только "Цены ТД ТОРЭКС")
        logger.info("   ➤ Загрузка базовой цены (Цены ТД ТОРЭКС) из первого файла...")
        for price in parse_base_prices_streaming(base_price_xml_path, only_price_type="Цены ТД ТОРЭКС"):
            base_prices.append(price)
        logger.info(f"      Найдено записей: {len(base_prices)}")
        
        # 1.2. Остальные базовые цены из второго файла
        logger.info("   ➤ Загрузка остальных базовых цен из второго файла...")
        count_second = 0
        for price in parse_base_prices_streaming(all_prices_xml_path, exclude_price_type="Цены ТД ТОРЭКС"):
            base_prices.append(price)
            count_second += 1
        logger.info(f"      Найдено записей: {count_second}")
        
        # Сохраняем пакетно
        logger.info(f"   ➤ Сохранение {len(base_prices)} базовых цен в БД...")
        count_base = save_base_prices_batch(conn, base_prices)
        logger.info(f"      Сохранено базовых цен: {count_base}")
        
        # ==================== 2. ДОПОЛНИТЕЛЬНЫЕ ОПЦИИ ====================
        logger.info("\n📊 Обработка дополнительных опций...")
        
        # Собираем опции
        logger.info("   ➤ Загрузка опций из второго файла...")
        options = list(parse_additional_options_streaming(all_prices_xml_path))
        logger.info(f"      Найдено опций: {len(options)}")
        
        # Сохраняем пакетно
        logger.info("   ➤ Сохранение опций и условий в БД...")
        count_options = save_options_with_conditions(conn, options)
        logger.info(f"      Сохранено опций: {count_options}")
    
    logger.info("\n✅ Обновление БД завершено!")
    
    # Выводим статистику
    with get_db_connection(sqlite_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM BasePrices")
        total_base = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM AdditionalOptions")
        total_options = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM OptionConditions")
        total_conditions = cursor.fetchone()[0]
        
        logger.info("\n📊 Статистика БД:")
        logger.info(f"   - Базовых цен: {total_base}")
        logger.info(f"   - Дополнительных опций: {total_options}")
        logger.info(f"   - Условий: {total_conditions}")



    
        
    


if __name__ == '__main__':
    from config import Config
    
    # Пути к файлам
    base_price_xml = Config.BASE_PRICE_XML
    all_prices_xml = Config.ALL_PRICES_XML
    db_path = Config.NEW_PATH_TO_PRICE_DB

    logger.info(f"Файл с базовой ценой: {base_price_xml}")
    logger.info(f"Файл со всеми ценами: {all_prices_xml}")
    logger.info(f"База данных: {db_path}")

    # Запускаем обновление
    update_price_db_from_xml(
        base_price_xml, 
        all_prices_xml, 
        db_path,
        clear_existing=True  # Можно изменить на False для инкрементального обновления
    )
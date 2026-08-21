"""
database.py - Модуль для работы с базой данных SQLite
"""
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Класс для управления базой данных SQLite"""
    
    DB_PATH = Path(__file__).parent.parent /"database/orders.db"
    
    @classmethod
    def init_db(cls) -> bool:
        """
        Инициализирует базу данных и создает таблицу если её нет
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Contract (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ContractID TEXT NOT NULL UNIQUE,
                    CustomerName TEXT DEFAULT '-',
                    Model TEXT DEFAULT '-',
                    Width TEXT DEFAULT '-',
                    Height TEXT DEFAULT '-',
                    Hinge TEXT DEFAULT '-',
                    OutPic TEXT DEFAULT '-',
                    OutColor TEXT DEFAULT '-',
                    InPic TEXT DEFAULT '-',
                    InColor TEXT DEFAULT '-',
                    Trim TEXT DEFAULT '-',
                    TrimColor TEXT DEFAULT '-',
                    Furniture TEXT DEFAULT '-',
                    Montage TEXT DEFAULT '-',
                    AdvanceOptions TEXT DEFAULT '-',
                    DocumentationPath TEXT DEFAULT '-',
                    Notes TEXT DEFAULT '-',
                    peep TEXT DEFAULT '-',
                    peep_offset TEXT DEFAULT '-',
                    manager TEXT DEFAULT '-',
                    Head TEXT DEFAULT '-',
                    HeadPicOut TEXT DEFAULT '-',
                    HeadPicIn TEXT DEFAULT '-',
                    vff TEXT DEFAULT '-',
                    zff TEXT DEFAULT '-',
                    pff TEXT DEFAULT '-',
                    ff_pic TEXT DEFAULT '-',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ База данных инициализирована: {cls.DB_PATH}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            return False
    
    @classmethod
    def save_contract(cls, data: Dict[str, Any], contract_id: str, doc_path: str) -> bool:
        """
        Сохраняет данные заказа в базу данных
        
        Args:
            data: словарь с данными заказа
            contract_id: ID контракта
            doc_path: путь к документации
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        # Функция для замены None и пустых строк на '-'
        def safe_str(value):
            if value is None or value == '':
                return '-'
            return str(value)
        
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Формируем опции как строку через запятую
            options = data.get('options', [])
            advance_options = ', '.join(options) if options else '-'
            
            # Преобразуем булевы значения в строки
            peep = '1' if data.get('peep', False) else '0'
            peep_offset = '1' if data.get('peep_offset', False) else '0'
            head = '1' if data.get('head', False) else '0'
            
            cursor.execute('''
                INSERT OR REPLACE INTO Contract (
                    ContractID, CustomerName, Model, Width, Height, Hinge,
                    OutPic, OutColor, InPic, InColor, Trim, TrimColor,
                    Furniture, Montage, AdvanceOptions, DocumentationPath, Notes,
                    peep, peep_offset, manager, Head, HeadPicOut, HeadPicIn,
                    vff, zff, pff, ff_pic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contract_id,
                safe_str(data.get('customer_name')),
                safe_str(data.get('model')),
                safe_str(data.get('01_Ширина')),
                safe_str(data.get('02_Высота')),
                safe_str(data.get('03_Петли')),
                safe_str(data.get('05_Лицо (рисунок)')),
                safe_str(data.get('04_Лицо (цвет)')),
                safe_str(data.get('07_Внутр. отделка (рисунок)')),
                safe_str(data.get('06_Внутр. отделка (цвет)')),
                safe_str(data.get('10_Обналичка')),
                safe_str(
                    data.get('11_Обналичка (цвет)')
                    or data.get('trim_color', '-')
                ),
                safe_str(data.get('08_Фурнитура')),
                safe_str(data.get('09_Монтаж')),
                advance_options,
                doc_path,
                safe_str(data.get('notes')),
                peep,
                peep_offset,
                safe_str(data.get('manager')),
                head,
                safe_str(data.get('head_pic_out', '-')),
                safe_str(data.get('head_pic_in', '-')),
                safe_str(data.get('vff', 0)),
                safe_str(data.get('zff', 0)),
                safe_str(data.get('pff', 0)),
                safe_str(data.get('ff_pic', '-'))
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Данные заказа сохранены в БД: ContractID={contract_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения данных в БД: {e}")
            return False
    
    @classmethod
    def get_contract(cls, contract_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные заказа по ID
        
        Args:
            contract_id: ID контракта
        
        Returns:
            словарь с данными заказа или None
        """
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM Contract WHERE ContractID = ?', (contract_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения заказа из БД: {e}")
            return None
    
    @classmethod
    def get_all_contracts(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получает все заказы
        
        Args:
            limit: максимальное количество записей
        
        Returns:
            список словарей с данными заказов
        """
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ContractID, Model, Width, Height, created_at 
                FROM Contract 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            
            conn.close()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка заказов: {e}")
            return []
    
    @classmethod
    def get_contracts_count(cls) -> int:
        """
        Получает количество заказов в базе
        
        Returns:
            int: количество заказов
        """
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM Contract')
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета заказов: {e}")
            return 0
    
    @classmethod
    def delete_contract(cls, contract_id: str) -> bool:
        """
        Удаляет заказ из базы данных
        
        Args:
            contract_id: ID контракта
        
        Returns:
            bool: True если успешно
        """
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            cursor.execute('DELETE FROM Contract WHERE ContractID = ?', (contract_id,))
            conn.commit()
            conn.close()
            logger.info(f"✅ Заказ {contract_id} удален из БД")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления заказа: {e}")
            return False

    @classmethod
    def find_order(cls, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Поиск заказа по ID (аналог get_contract, но с форматированием для API)
        
        Args:
            order_id: ID заказа для поиска
            
        Returns:
            словарь с данными заказа, отформатированный для API
        """
        try:
            order = cls.get_contract(order_id)
            
            if not order:
                logger.info(f"⚠️ Заказ не найден: {order_id}")
                return None
            
            # Преобразуем данные для API
            result = {
                'ContractID': order.get('ContractID', ''),
                'CustomerName': order.get('CustomerName', ''),
                'Model': order.get('Model', ''),
                'Width': order.get('Width', ''),
                'Height': order.get('Height', ''),
                'Hinge': order.get('Hinge', ''),
                'OutPic': order.get('OutPic', ''),
                'OutColor': order.get('OutColor', ''),
                'InPic': order.get('InPic', ''),
                'InColor': order.get('InColor', ''),
                'Trim': order.get('Trim', ''),
                'TrimColor': order.get('TrimColor', ''),
                'Furniture': order.get('Furniture', ''),
                'Montage': order.get('Montage', ''),
                'AdvanceOptions': order.get('AdvanceOptions', ''),
                'DocumentationPath': order.get('DocumentationPath', ''),
                'Notes': order.get('Notes', ''),
                'peep': 0 if order.get('peep') == '0' else 1,
                'peep_offset': 0 if order.get('peep_offset') == '0' else 1,
                'manager': order.get('manager', ''),
                'Head': 0 if order.get('Head') == '0' else 1,
                'HeadPicOut': order.get('HeadPicOut', ''),
                'HeadPicIn': order.get('HeadPicIn', ''),
                'vff': int(order.get('vff', '0')),
                'zff': int(order.get('zff', '0')),
                'pff': int(order.get('pff', '0')),
                'ff_pic': order.get('ff_pic', ''),
                'created_at': order.get('created_at', '')
            }
            
            # Удаляем None значения
            result = {k: v for k, v in result.items() if v is not None}
            
            logger.info(f"✅ Найден заказ: {order_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска заказа: {e}")
            return None
# =============================================================================
# Упрощенные функции для внешнего использования
# =============================================================================

def init_database() -> bool:
    """
    Инициализирует базу данных
    
    Returns:
        bool: True если успешно
    """
    return DatabaseManager.init_db()


def save_order_to_db(data: Dict[str, Any], contract_id: str, doc_path: str) -> bool:
    """
    Сохраняет заказ в базу данных
    
    Args:
        data: словарь с данными заказа
        contract_id: ID контракта
        doc_path: путь к документации
    
    Returns:
        bool: True если успешно
    """
    return DatabaseManager.save_contract(data, contract_id, doc_path)

def find_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Поиск заказа по ID (отформатированный для API)"""
    return DatabaseManager.find_order(order_id)


def get_order_from_db(contract_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает заказ из базы данных по ID
    
    Args:
        contract_id: ID контракта
    
    Returns:
        словарь с данными заказа или None
    """
    return DatabaseManager.get_contract(contract_id)


def get_all_orders_from_db(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Получает все заказы из базы данных
    
    Args:
        limit: максимальное количество записей
    
    Returns:
        список словарей с данными заказов
    """
    return DatabaseManager.get_all_contracts(limit)


def get_orders_count() -> int:
    """
    Получает количество заказов в базе
    
    Returns:
        int: количество заказов
    """
    return DatabaseManager.get_contracts_count()


# =============================================================================
# ТЕСТИРОВАНИЕ
# =============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ МОДУЛЯ DATABASE")
    print("="*60)
    
    # Тест инициализации БД
    print("\n📌 Тест 1: Инициализация БД")
    success = init_database()
    print(f"   Инициализация: {'✅ Успешно' if success else '❌ Ошибка'}")
    
    # Тест сохранения заказа
    print("\n📌 Тест 2: Сохранение заказа")
    test_data = {
        'customer_name': 'ООО "Тестовая Компания"',
        'model': 'DELTA PRO MP',
        '01_Ширина': 1000,
        '02_Высота': 2200,
        '03_Петли': 'R',
        '04_Лицо (цвет)': 'Белый',
        '05_Лицо (рисунок)': 'Busoni',
        '06_Внутр. отделка (цвет)': 'Белый',
        '07_Внутр. отделка (рисунок)': 'Castle',
        '08_Фурнитура': 'ЧКВ_AP15_AP15',
        '09_Монтаж': 'НАКЛ',
        '10_Обналичка': 'НУ-1',
        'notes': 'Тестовый заказ',
        'options': ['Опция 1', 'Опция 2'],
        'peep': True,
        'vff': 85,
        'zff': 85,
        'pff': 85,
        'manager': 'Иванов И.И.'
    }
    
    test_id = "TEST001"
    test_path = "/home/alex/TEST"
    
    success = save_order_to_db(test_data, test_id, test_path)
    print(f"   Сохранение: {'✅ Успешно' if success else '❌ Ошибка'}")
    
    # Тест получения заказа
    print("\n📌 Тест 3: Получение заказа")
    order = get_order_from_db(test_id)
    if order:
        print(f"   Найден заказ: {order['ContractID']}")
        print(f"   Модель: {order['Model']}")
        print(f"   Размер: {order['Width']}x{order['Height']}")
        print(f"   Менеджер: {order['manager']}")
    else:
        print("   ❌ Заказ не найден")
    
    # Тест получения списка заказов
    print("\n📌 Тест 4: Список заказов")
    orders = get_all_orders_from_db(limit=5)
    print(f"   Всего заказов: {get_orders_count()}")
    for order in orders:
        print(f"      {order['ContractID']} - {order['Model']} - {order['created_at']}")
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)

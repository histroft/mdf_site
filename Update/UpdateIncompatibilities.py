'''
Функция обновляет базу данных дверей, заполняя таблицу несовместимостей из Гугловской таблицы


Расширил возможности: Итак нам нужно сначала добавить несовместимости из таблицы Гугл, а затем
добавить данные из самой базы данных.

'''

import sqlite3
from datetime import time
from time import sleep

import gspread
import pygsheets
import os

from oauth2client.service_account import ServiceAccountCredentials

os.environ['HTTP_PROXY'] = 'http://1.1.1.40:3128'
os.environ['HTTPS_PROXY'] = 'http://1.1.1.40:3128'


def authorize_gspread():
    print("Starting authorized client...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path_to_file = str(os.path.dirname(os.path.abspath(__file__))) + '/credentials.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name(path_to_file, scope)
    client = gspread.authorize(creds)
    print("Connect succesful")
    return client



def update_manual_incompatibilities(sheet_url, db_name, batch_size=1000):
    """
    Обновляет таблицу Manual_incomp из Google Sheets
    Колонки: A-Модель, B-свойство1, C-характеристика1, D-свойство2, E-характеристика2, F-разрешение (1 или 0)
    """
    try:
        client = authorize_gspread()
        wks = client.open_by_url(sheet_url).worksheet("К выгрузке")

        # Получаем все данные
        print("📥 Загрузка данных из Google Sheets...")
        all_data = wks.get_all_values()
        
        if not all_data or len(all_data) <= 1:
            print("❌ Нет данных для обработки")
            return False
            
        total_rows = len(all_data)
        print(f"📊 Всего строк в таблице: {total_rows}")
        print(f"📋 Заголовки: {all_data[0]}")  # Показываем заголовки для проверки

        processed_count = 0
        error_count = 0
        
        with sqlite3.connect(db_name, timeout=10) as conn:
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет
            create_manual_incomp_table(conn)
            
            for i in range(1, total_rows):  # Пропускаем заголовок (строка 0)
                row = all_data[i]
                
                # Пропускаем пустые строки
                if not row or len(row) < 6:
                    continue
                
                # Извлекаем данные по колонкам
                model_name = row[0].strip() if len(row) > 0 else ""
                prop1_name = row[1].strip() if len(row) > 1 else ""
                value1 = row[2].strip() if len(row) > 2 else ""
                prop2_name = row[3].strip() if len(row) > 3 else ""
                value2 = row[4].strip() if len(row) > 4 else ""
                resolution_str = row[5].strip() if len(row) > 5 else "0"
                
                # Проверяем обязательные поля
                if not all([model_name, prop1_name, value1, prop2_name, value2]):
                    print(f"⚠️  Строка {i+1}: пропущена - не заполнены обязательные поля")
                    continue
                
                # Преобразуем разрешение в число
                try:
                    resolution = 1 if resolution_str in ["1", "да", "yes", "true", "разрешено"] else 0
                except:
                    resolution = 0
                
                try:
                    add_manual_incompatibility_record(
                        conn=conn,
                        cursor=cursor,
                        model_name=model_name,
                        prop1_name=prop1_name,
                        value1=value1,
                        prop2_name=prop2_name,
                        value2=value2,
                        resolution=resolution
                    )
                    processed_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Ошибка в строке {i+1}: {e}")
                    print(f"   Данные: {model_name} | {prop1_name}={value1} | {prop2_name}={value2} | разрешение={resolution}")

                # Фиксируем изменения пачками
                if processed_count % batch_size == 0:
                    conn.commit()
                    print(f"⏳ Обработано: {processed_count} строк")
                    sleep(1)  # Задержка для API

            # Финальное сохранение
            conn.commit()
            
        print(f"\n✅ Импорт завершён!")
        print(f"📈 Обработано записей: {processed_count}")
        print(f"❌ Ошибок: {error_count}")
        
        return True

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False
    
    
    
    
def add_manual_incompatibility_record(conn, cursor, model_name, prop1_name, value1, 
                                     prop2_name, value2, resolution=0, comment=""):
    """
    Добавляет или обновляет запись в Manual_incomp
    """
    # Получаем ID модели и свойств
    cursor.execute("SELECT model_id FROM models WHERE model_name = ?", (model_name,))
    model_row = cursor.fetchone()
    if not model_row:
        raise ValueError(f"Модель '{model_name}' не найдена в базе")
    model_id = model_row[0]
    
    cursor.execute("SELECT property_id FROM properties WHERE property_name = ?", (prop1_name,))
    prop1_row = cursor.fetchone()
    if not prop1_row:
        raise ValueError(f"Свойство '{prop1_name}' не найдено в базе")
    prop1_id = prop1_row[0]
    
    cursor.execute("SELECT property_id FROM properties WHERE property_name = ?", (prop2_name,))
    prop2_row = cursor.fetchone()
    if not prop2_row:
        raise ValueError(f"Свойство '{prop2_name}' не найдено в базе")
    prop2_id = prop2_row[0]
    
    # Проверяем, существует ли уже такая запись
    cursor.execute("""
    SELECT manual_id FROM Manual_incomp 
    WHERE model_id = ? 
      AND property1_id = ? AND value1 = ?
      AND property2_id = ? AND value2 = ?
    """, (model_id, prop1_id, value1, prop2_id, value2))
    
    existing_record = cursor.fetchone()
    
    if existing_record:
        # Обновляем существующую запись
        cursor.execute("""
        UPDATE Manual_incomp 
        SET resolution = ?, comment = ?, updated_date = CURRENT_TIMESTAMP
        WHERE manual_id = ?
        """, (resolution, comment, existing_record[0]))
        print(f"   🔄 Обновлена запись: {model_name} | {prop1_name}={value1} | {prop2_name}={value2}")
    else:
        # Добавляем новую запись
        cursor.execute("""
        INSERT INTO Manual_incomp 
        (model_id, model_name, property1_id, property1_name, value1, 
         property2_id, property2_name, value2, resolution, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (model_id, model_name, prop1_id, prop1_name, value1, 
              prop2_id, prop2_name, value2, resolution, comment))
        print(f"   ✅ Добавлена запись: {model_name} | {prop1_name}={value1} | {prop2_name}={value2}")






def update_incompatibilities_old(sheet_url, db_name, batch_size=1000):  # Увеличили batch_size
    try:
        client = authorize_gspread()
        wks = client.open_by_url(sheet_url).worksheet("К выгрузке")

        # Получаем все данные сразу (если это возможно)
        print("Загрузка данных...")
        all_data = wks.get_all_values()
        total_rows = len(all_data)
        print(f"Всего строк: {total_rows - 1}")

        with sqlite3.connect(db_name, timeout=10) as conn:
            cursor = conn.cursor()
            for i in range(1, total_rows):  # Пропускаем заголовок (строка 0)
                row = all_data[i]
                print(f"Строка {i}: {row}")
                if len(row) < 5:
                    continue

                try:
                    add_incompatibility(
                        conn=conn,
                        cursor=cursor,
                        model_name=row[0].strip(),
                        prop1_name=row[1].strip(),
                        value1=row[2].strip(),
                        prop2_name=row[3].strip(),
                        value2=row[4].strip()
                    )
                except Exception as e:
                    print(f"Ошибка в строке {i + 1}: {e}")

                # Фиксируем каждые N строк
                if i % batch_size == 0:
                    conn.commit()
                    print(f"Обработано: {i}/{total_rows - 1}")
                    sleep(2)  # Задержка для API

            conn.commit()  # Финальное сохранение

        print("Импорт завершён!")
        return True

    except Exception as e:
        print(f"Ошибка: {e}")
        return False


def add_incompatibility(conn, cursor, model_name, prop1_name, value1, prop2_name, value2):
    """
    Добавляет несовместимость между двумя свойствами модели,
    учитывая новую структуру таблицы incompatibilities.
    """
    try:
        # Получаем model_id
        cursor.execute('SELECT model_id FROM models WHERE model_name = ?', (model_name,))
        res = cursor.fetchone()
        if not res:
            raise ValueError(f"Модель '{model_name}' не найдена в базе")
        model_id = res[0]

        # Получаем property1_id
        cursor.execute('SELECT property_id FROM properties WHERE property_name = ?', (prop1_name,))
        res = cursor.fetchone()
        if not res:
            raise ValueError(f"Свойство '{prop1_name}' не найдено в базе")
        property1_id = res[0]

        # Получаем property2_id
        cursor.execute('SELECT property_id FROM properties WHERE property_name = ?', (prop2_name,))
        res = cursor.fetchone()
        if not res:
            raise ValueError(f"Свойство '{prop2_name}' не найдено в базе")
        property2_id = res[0]

        # Проверка дубликатов
        cursor.execute('''
            SELECT 1 FROM incompatibilities
            WHERE model_id = ? AND (
                (property1_id = ? AND value1 = ? AND property2_id = ? AND value2 = ?)
                OR
                (property1_id = ? AND value1 = ? AND property2_id = ? AND value2 = ?)
            )
        ''', (
            model_id, property1_id, value1, property2_id, value2,
            property2_id, value2, property1_id, value1
        ))

        if cursor.fetchone():
            return False  # Дубликат найден

        # Добавляем новую запись
        cursor.execute('''
            INSERT INTO incompatibilities (model_id, property1_id, value1, property2_id, value2) 
            VALUES (?, ?, ?, ?, ?)
        ''', (model_id, property1_id, value1, property2_id, value2))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise
    
    

    """Эта функция ищет несовместимости только для моделей, имеющих исполнения с '#777'"""
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    # 1. Находим модели, у которых есть исполнения с "#777"
    print("🔍 Поиск моделей с исполнениями #777...")
    cur.execute("""
    SELECT DISTINCT m.model_id, m.model_name 
    FROM models m
    JOIN variants v ON m.model_id = v.model_id
    WHERE v.unique_combination LIKE '%#777%'
    AND m.model_name NOT LIKE '%.Комплект О3%'
    AND m.model_name NOT LIKE '%Панель%'
    AND m.model_name NOT LIKE '%Добор%'
    ORDER BY m.model_name
    """)
    
    models_with_777 = cur.fetchall()
    
    if not models_with_777:
        print("❌ Не найдено моделей с исполнениями #777")
        conn.close()
        return 0
    
    print(f"✅ Найдено моделей с #777: {len(models_with_777)}")
    for model_id, model_name in models_with_777:
        print(f"   📦 {model_name} (ID: {model_id})")
    
    # Пары свойств для проверки
    property_pairs = [
        ("01_Ширина", "04_Лицо (цвет)"),
        ("01_Ширина", "05_Лицо (рисунок)"),
        ("01_Ширина", "06_Внутр. отделка (цвет)"),
        ("01_Ширина", "07_Внутр. отделка (рисунок)"),
        ("02_Высота", "04_Лицо (цвет)"),
        ("02_Высота", "05_Лицо (рисунок)"),
        ("02_Высота", "06_Внутр. отделка (цвет)"),
        ("02_Высота", "07_Внутр. отделка (рисунок)"),
        ("04_Лицо (цвет)", "05_Лицо (рисунок)"),
        ("06_Внутр. отделка (цвет)", "07_Внутр. отделка (рисунок)")
    ]
    
    # Получаем ID свойств
    cur.execute("SELECT property_id, property_name FROM properties")
    property_ids = {prop_name: prop_id for prop_id, prop_name in cur.fetchall()}
    
    total_incompatibilities = 0
    new_incompatibilities = 0
    existing_incompatibilities = 0
    
    # 2. Для каждой модели из списка ищем несовместимости
    for model_id, model_name in models_with_777:
        print(f"\n🔍 Анализируем модель: {model_name}")
        
        for prop1_name, prop2_name in property_pairs:
            prop1_id = property_ids.get(prop1_name)
            prop2_id = property_ids.get(prop2_name)
            
            if not prop1_id or not prop2_id:
                continue
            
            # 1. Получаем значения для этих свойств ТОЛЬКО ДЛЯ ТЕКУЩЕЙ МОДЕЛИ (исключая #777)
            cur.execute("""
            SELECT DISTINCT c.value 
            FROM characteristics c
            JOIN variants v ON c.variant_id = v.variant_id
            WHERE v.model_id = ?
              AND c.property_id = ? 
              AND v.unique_combination NOT LIKE '%#777%'
            """, (model_id, prop1_id))
            model_values1 = [str(row[0]) for row in cur.fetchall() if row[0] is not None]
            
            cur.execute("""
            SELECT DISTINCT c.value 
            FROM characteristics c
            JOIN variants v ON c.variant_id = v.variant_id
            WHERE v.model_id = ?
              AND c.property_id = ? 
              AND v.unique_combination NOT LIKE '%#777%'
            """, (model_id, prop2_id))
            model_values2 = [str(row[0]) for row in cur.fetchall() if row[0] is not None]
            
            if not model_values1 or not model_values2:
                continue
            
            # 2. Получаем существующие комбинации ТОЛЬКО ДЛЯ ТЕКУЩЕЙ МОДЕЛИ (исключая #777)
            cur.execute("""
            SELECT DISTINCT c1.value, c2.value
            FROM variants v
            JOIN characteristics c1 ON v.variant_id = c1.variant_id
            JOIN characteristics c2 ON v.variant_id = c2.variant_id
            WHERE v.model_id = ?
              AND v.unique_combination NOT LIKE '%#777%'
              AND c1.property_id = ?
              AND c2.property_id = ?
            """, (model_id, prop1_id, prop2_id))
            
            existing_combinations = set()
            for row in cur.fetchall():
                if row[0] is not None and row[1] is not None:
                    existing_combinations.add((str(row[0]), str(row[1])))
            
            # 3. Генерируем все возможные комбинации для модели
            all_possible_combinations = set()
            for v1 in model_values1:
                for v2 in model_values2:
                    all_possible_combinations.add((v1, v2))
            
            # 4. Находим несовместимости для этой модели
            missing_combinations = all_possible_combinations - existing_combinations
            
            if missing_combinations:
                print(f"   🚫 {prop1_name} ↔ {prop2_name}: {len(missing_combinations)} несовместимостей")
            
            # 5. Сохраняем несовместимости с привязкой к модели
            batch_data = []
            pair_new_count = 0
            pair_existing_count = 0
            
            for val1, val2 in missing_combinations:
                # Проверяем, существует ли уже такая запись
                cur.execute("""
                SELECT 1 FROM incompatibilities 
                WHERE model_id = ? 
                  AND property1_id = ? AND value1 = ? 
                  AND property2_id = ? AND value2 = ?
                LIMIT 1
                """, (model_id, prop1_id, val1, prop2_id, val2))
                
                exists = cur.fetchone() is not None
                
                if not exists:
                    # Проверяем обратную комбинацию
                    cur.execute("""
                    SELECT 1 FROM incompatibilities 
                    WHERE model_id = ? 
                      AND property1_id = ? AND value1 = ? 
                      AND property2_id = ? AND value2 = ?
                    LIMIT 1
                    """, (model_id, prop2_id, val2, prop1_id, val1))
                    
                    reverse_exists = cur.fetchone() is not None
                    
                    if not reverse_exists:
                        batch_data.append((model_id, prop1_id, val1, prop2_id, val2))
                        pair_new_count += 1
                    else:
                        pair_existing_count += 1
                else:
                    pair_existing_count += 1
            
            # Вставляем данные пачкой
            if batch_data:
                cur.executemany("""
                INSERT INTO incompatibilities (model_id, property1_id, value1, property2_id, value2)
                VALUES (?, ?, ?, ?, ?)
                """, batch_data)
            
            total_incompatibilities += len(missing_combinations)
            new_incompatibilities += pair_new_count
            existing_incompatibilities += pair_existing_count
            
            if pair_new_count > 0:
                print(f"   💾 Добавлено {pair_new_count} новых несовместимостей")
    
    # Сохраняем изменения
    conn.commit()
    
    # Итоговая статистика
    cur.execute("SELECT COUNT(*) FROM incompatibilities")
    total_in_db = cur.fetchone()[0]
    
    conn.close()
    
    print(f"\n🎯 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"   📊 Проанализировано моделей с #777: {len(models_with_777)}")
    print(f"   🔍 Всего несовместимостей найдено: {total_incompatibilities}")
    print(f"   💾 Новых добавлено в базу: {new_incompatibilities}")
    print(f"   🔄 Уже существовало в базе: {existing_incompatibilities}")
    print(f"   📁 Всего записей в таблице incompatibilities: {total_in_db}")
    
    return new_incompatibilities

def find_and_save_incompatibilities_to_db(db_file):
    """Функция ищет несовместимости между парами свойств для ВСЕХ моделей и ВСЕХ их исполнений, исключая #777
    Алгоритм поиска несовместимостей:
1. Составляется список моделей в исполнениях которых отсутствует "777"
2. Берутся все свойства для определенных характеристик встречающиеся во всех исполнениях данной модели
    ("01_Ширина", "04_Лицо (цвет)"),
        ("01_Ширина", "05_Лицо (рисунок)"),
        ("01_Ширина", "06_Внутр. отделка (цвет)"),
        ("01_Ширина", "07_Внутр. отделка (рисунок)"),
        ("02_Высота", "04_Лицо (цвет)"),
        ("02_Высота", "05_Лицо (рисунок)"),
        ("02_Высота", "06_Внутр. отделка (цвет)"),
        ("02_Высота", "07_Внутр. отделка (рисунок)"),
        ("04_Лицо (цвет)", "05_Лицо (рисунок)"),
        ("06_Внутр. отделка (цвет)", "07_Внутр. отделка (рисунок)"
То есть все значения ширин, высот, лицевой и внутренней отделки.
4. По этому списку определяется какие комбинации этих пар никогда не встречаются вместе.
...
Profit!"""
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    # 1. Находим ВСЕ модели для анализа
    print("🔍 Поиск всех моделей для анализа...")
    cur.execute("""
    SELECT DISTINCT m.model_id, m.model_name 
    FROM models m
    WHERE m.model_name NOT LIKE '%.Комплект О3%'
    AND m.model_name NOT LIKE '%Панель%'
    AND m.model_name NOT LIKE '%Добор%'
    ORDER BY m.model_name
    """)
    
    all_models = cur.fetchall()
    
    if not all_models:
        print("❌ Не найдено моделей для анализа")
        conn.close()
        return 0
    
    print(f"✅ Найдено моделей для анализа: {len(all_models)}")
    
    # Пары свойств для проверки
    property_pairs = [
        ("01_Ширина", "04_Лицо (цвет)"),    #1
        ("01_Ширина", "05_Лицо (рисунок)"), #2
        ("01_Ширина", "06_Внутр. отделка (цвет)"),  #3
        ("01_Ширина", "07_Внутр. отделка (рисунок)"),   #4
        ("02_Высота", "04_Лицо (цвет)"),                #5
        ("02_Высота", "05_Лицо (рисунок)"),             #6
        ("02_Высота", "06_Внутр. отделка (цвет)"),      #7
        ("02_Высота", "07_Внутр. отделка (рисунок)"),   #8
        ("04_Лицо (цвет)", "05_Лицо (рисунок)"),        #9
        ("06_Внутр. отделка (цвет)", "07_Внутр. отделка (рисунок)"), #10
        ("01_Ширина", "02_Высота"),                                    #11
        ("02_Высота","10_Обналичка"),                                #12
        ("01_Ширина", "10_Обналичка"),                              #13
        
    ]
    
    # Получаем ID свойств
    cur.execute("SELECT property_id, property_name FROM properties")
    property_ids = {prop_name: prop_id for prop_id, prop_name in cur.fetchall()}
    
    total_incompatibilities = 0
    new_incompatibilities = 0
    existing_incompatibilities = 0
    
    # 2. Для КАЖДОЙ модели анализируем ВСЕ исполнения (кроме #777)
    for model_id, model_name in all_models:
        print(f"\n🔍 Анализируем модель: {model_name}")
        
        # Получаем количество исполнений для этой модели (исключая #777)
        cur.execute("""
        SELECT COUNT(*) 
        FROM variants v 
        WHERE v.model_id = ? 
        AND v.unique_combination NOT LIKE '%#777%'
        """, (model_id,))
        
        variant_count = cur.fetchone()[0]
        
        if variant_count == 0:
            print(f"   ⏭️ Пропускаем - нет исполнений (кроме #777)")
            continue
            
        print(f"   📊 Исполнений для анализа: {variant_count}")
        
        for prop1_name, prop2_name in property_pairs:
            prop1_id = property_ids.get(prop1_name)
            prop2_id = property_ids.get(prop2_name)
            
            if not prop1_id or not prop2_id:
                continue
            
            # 1. Получаем значения для этих свойств ДЛЯ ТЕКУЩЕЙ МОДЕЛИ (исключая #777)
            cur.execute("""
            SELECT DISTINCT c.value 
            FROM characteristics c
            JOIN variants v ON c.variant_id = v.variant_id
            WHERE v.model_id = ?
              AND c.property_id = ? 
              AND v.unique_combination NOT LIKE '%#777%'
            """, (model_id, prop1_id))
            model_values1 = [str(row[0]) for row in cur.fetchall() if row[0] is not None]
            
            cur.execute("""
            SELECT DISTINCT c.value 
            FROM characteristics c
            JOIN variants v ON c.variant_id = v.variant_id
            WHERE v.model_id = ?
              AND c.property_id = ? 
              AND v.unique_combination NOT LIKE '%#777%'
            """, (model_id, prop2_id))
            model_values2 = [str(row[0]) for row in cur.fetchall() if row[0] is not None]
            
            if not model_values1 or not model_values2:
                continue
            
            # 2. Получаем существующие комбинации ДЛЯ ТЕКУЩЕЙ МОДЕЛИ (исключая #777)
            cur.execute("""
            SELECT DISTINCT c1.value, c2.value
            FROM variants v
            JOIN characteristics c1 ON v.variant_id = c1.variant_id
            JOIN characteristics c2 ON v.variant_id = c2.variant_id
            WHERE v.model_id = ?
              AND v.unique_combination NOT LIKE '%#777%'
              AND c1.property_id = ?
              AND c2.property_id = ?
            """, (model_id, prop1_id, prop2_id))
            
            existing_combinations = set()
            for row in cur.fetchall():
                if row[0] is not None and row[1] is not None:
                    existing_combinations.add((str(row[0]), str(row[1])))
            
            # 3. Генерируем все возможные комбинации для модели
            all_possible_combinations = set()
            for v1 in model_values1:
                for v2 in model_values2:
                    all_possible_combinations.add((v1, v2))
            
            # 4. Находим несовместимости для этой модели
            missing_combinations = all_possible_combinations - existing_combinations
            
            if missing_combinations:
                print(f"   🚫 {prop1_name} ↔ {prop2_name}: {len(missing_combinations)} несовместимостей")
            
            # 5. Сохраняем несовместимости с привязкой к модели
            batch_data = []
            pair_new_count = 0
            pair_existing_count = 0
            
            for val1, val2 in missing_combinations:
                # Проверяем, существует ли уже такая запись
                cur.execute("""
                SELECT 1 FROM incompatibilities 
                WHERE model_id = ? 
                  AND property1_id = ? AND value1 = ? 
                  AND property2_id = ? AND value2 = ?
                LIMIT 1
                """, (model_id, prop1_id, val1, prop2_id, val2))
                
                exists = cur.fetchone() is not None
                
                if not exists:
                    # Проверяем обратную комбинацию
                    cur.execute("""
                    SELECT 1 FROM incompatibilities 
                    WHERE model_id = ? 
                      AND property1_id = ? AND value1 = ? 
                      AND property2_id = ? AND value2 = ?
                    LIMIT 1
                    """, (model_id, prop2_id, val2, prop1_id, val1))
                    
                    reverse_exists = cur.fetchone() is not None
                    
                    if not reverse_exists:
                        batch_data.append((model_id, prop1_id, val1, prop2_id, val2))
                        pair_new_count += 1
                    else:
                        pair_existing_count += 1
                else:
                    pair_existing_count += 1
            
            # Вставляем данные пачкой
            if batch_data:
                cur.executemany("""
                INSERT INTO incompatibilities (model_id, property1_id, value1, property2_id, value2)
                VALUES (?, ?, ?, ?, ?)
                """, batch_data)
                print(f"   💾 Добавлено {pair_new_count} новых несовместимостей")
            
            total_incompatibilities += len(missing_combinations)
            new_incompatibilities += pair_new_count
            existing_incompatibilities += pair_existing_count
    
    # Сохраняем изменения
    conn.commit()
    
    # Итоговая статистика
    cur.execute("SELECT COUNT(*) FROM incompatibilities")
    total_in_db = cur.fetchone()[0]
    
    conn.close()
    
    print(f"\n🎯 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"   📊 Проанализировано моделей: {len(all_models)}")
    print(f"   🔍 Всего несовместимостей найдено: {total_incompatibilities}")
    print(f"   💾 Новых добавлено в базу: {new_incompatibilities}")
    print(f"   🔄 Уже существовало в базе: {existing_incompatibilities}")
    print(f"   📁 Всего записей в таблице incompatibilities: {total_in_db}")


def create_manual_incomp_table(db_file):
    
    """
    Создает таблицу для ручного управления несовместимостями в базе данных
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Manual_incomp (
            manual_id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER,
            model_name TEXT,
            property1_id INTEGER,
            property1_name TEXT,
            value1 TEXT,
            property2_id INTEGER,
            property2_name TEXT,
            value2 TEXT,
            resolution INTEGER NOT NULL DEFAULT 0,  -- 0 = несовместимо, 1 = разрешено
            comment TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (model_id) REFERENCES models (model_id),
            FOREIGN KEY (property1_id) REFERENCES properties (property_id),
            FOREIGN KEY (property2_id) REFERENCES properties (property_id)
        )
        """)
        
        # Создаем индекс для быстрого поиска
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_manual_incomp_search 
        ON Manual_incomp (model_id, property1_id, value1, property2_id, value2)
        """)
        
        conn.commit()
        print("✅ Таблица Manual_incomp создана успешно")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы: {e}")
    finally:
        conn.close()


# Основной вызов
if __name__ == "__main__":
    db_name = "/home/alex/temp/doors.db"
    #create_manual_incomp_table(db_file)
    
    sheet_url = "https://docs.google.com/spreadsheets/d/1aF6ZJNr47jAI1Gjt-EGOU8Se-kYNs9F-4KNQ_UQJG4k/edit?gid=906665945#gid=906665945"

    
    # Обновляем данные из Google Sheets
    success = update_manual_incompatibilities(sheet_url, db_name)
    
    
  
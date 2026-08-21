import csv
from itertools import product
import sqlite3
import time

def find_and_save_global_incompatibilities_non_models(db_file):
    """
    Сначала создаем CSV файл, так как у него получился идеальный алгоритм. 
    Затем из получившегося CSV загружаем данные в базу.
    """
    print("=== ПОИСК И СОХРАНЕНИЕ АВТОМАТИЧЕСКИХ НЕСОВМЕСТИМОСТЕЙ ===")
    
    scv_name = "/home/alex/temp/incompat_for_bd.csv"
    print(f'Создаем файл CSV: {scv_name}')
    find_global_incompatibilities(db_file, scv_name)
    
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA busy_timeout = 30000")
    cur = conn.cursor()
    
    # 1. НАСТРАИВАЕМ ПРАВИЛЬНЫЕ ТАБЛИЦЫ И СТОЛБЦЫ
    print("🔍 Настройка структуры базы данных...")
    
    properties_table = 'properties'
    properties_id_column = 'property_id'
    properties_name_column = 'property_name'
    
    print(f"🎯 Используем таблицу: {properties_table}")
    
    # 2. ЧИТАЕМ CSV И ОБРАБАТЫВАЕМ СВОЙСТВА
    print(f"📥 Чтение данных из CSV: {scv_name}")
    incompatibility_pairs = []
    
    # Собираем все уникальные свойства из CSV
    all_properties = set()
    
    with open(scv_name, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        
        try:
            headers = next(reader)
            print(f"📋 Заголовки CSV: {headers}")
        except StopIteration:
            print("ℹ️  CSV файл не содержит заголовков")
        
        # Первый проход: собираем все свойства
        csvfile.seek(0)
        try:
            headers = next(reader)
        except StopIteration:
            pass
        
        for i, row in enumerate(reader, 1):
            if len(row) >= 4:
                property1_name = row[0].strip()
                property2_name = row[2].strip()
                
                if property1_name:
                    all_properties.add(property1_name)
                if property2_name:
                    all_properties.add(property2_name)
    
    print(f"📝 Найдено уникальных свойств в CSV: {len(all_properties)}")
    
    # 3. СОЗДАЕМ ОТСУТСТВУЮЩИЕ СВОЙСТВА В БАЗЕ
    print("🔄 Создаем отсутствующие свойства в базе...")
    property_id_map = {}
    
    for prop_name in all_properties:
        property_id = get_or_create_property_id(cur, properties_table, properties_id_column, properties_name_column, prop_name)
        if property_id:
            property_id_map[prop_name] = property_id
        else:
            print(f"❌ Не удалось создать/найти свойство: {prop_name}")
    
    print(f"✅ Сопоставлено свойств: {len(property_id_map)}/{len(all_properties)}")
    
    # 4. ЧИТАЕМ CSV С ИСПОЛЬЗОВАНИЕМ ID
    print("📖 Чтение пар несовместимостей из CSV...")
    with open(scv_name, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        
        try:
            headers = next(reader)
        except StopIteration:
            pass
        
        for i, row in enumerate(reader, 1):
            if len(row) >= 4:
                property1_name = row[0].strip()
                value1 = row[1].strip()
                property2_name = row[2].strip()
                value2 = row[3].strip()
                
                if property1_name and value1 and property2_name and value2:
                    property1_id = property_id_map.get(property1_name)
                    property2_id = property_id_map.get(property2_name)
                    
                    if property1_id and property2_id:
                        incompatibility_pairs.append((property1_id, value1, property2_id, value2))
    
    print(f"✅ Прочитано пар из CSV: {len(incompatibility_pairs)}")
    
    if not incompatibility_pairs:
        print("❌ Нет данных для добавления в базу")
        conn.close()
        return 0
    
    # 5. ОЧИСТКА ТАБЛИЦЫ ПЕРЕД ВСТАВКОЙ
    print("🗑️  Очистка таблицы incompatibilities_non_models...")
    try:
        cur.execute("DELETE FROM incompatibilities_non_models")
        conn.commit()
        print("✅ Таблица успешно очищена")
    except Exception as e:
        print(f"❌ Ошибка при очистке таблицы: {e}")
        conn.rollback()
        conn.close()
        return 0
    
    # 6. ПРОВЕРКА НА ДУБЛИКАТЫ И ВСТАВКА
    print("🔍 Проверка на дубликаты и вставка данных...")
    
    # Используем множество для проверки дубликатов
    unique_pairs = set()
    duplicates_found = 0
    
    for pair in incompatibility_pairs:
        pair_tuple = tuple(pair)
        if pair_tuple in unique_pairs:
            duplicates_found += 1
        else:
            unique_pairs.add(pair_tuple)
    
    print(f"📊 Обнаружено дубликатов в данных: {duplicates_found}")
    print(f"📊 Уникальных записей для вставки: {len(unique_pairs)}")
    
    # Преобразуем обратно в список для вставки
    unique_pairs_list = list(unique_pairs)
    
    # 7. ОПТИМИЗИРОВАННАЯ ВСТАВКА УНИКАЛЬНЫХ ДАННЫХ
    print("💾 Вставка уникальных данных в базу...")
    
    added_count = 0
    batch_size = 1000
    total_batches = (len(unique_pairs_list) + batch_size - 1) // batch_size
    
    start_time = time.time()
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(unique_pairs_list))
        batch = unique_pairs_list[start_idx:end_idx]
        
        try:
            cur.executemany("""
                INSERT INTO incompatibilities_non_models 
                (property1_id, value1, property2_id, value2)
                VALUES (?, ?, ?, ?)
            """, batch)
            
            batch_added = len(batch)
            added_count += batch_added
            
            # Прогресс каждые 10 пакетов или последний пакет
            if batch_num % 10 == 0 or batch_num == total_batches - 1:
                elapsed = time.time() - start_time
                progress = (batch_num + 1) / total_batches * 100
                print(f"📦 Пакет {batch_num + 1}/{total_batches} ({progress:.1f}%) - добавлено: {batch_added}")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Ошибка в пакете {batch_num + 1}: {e}")
            conn.rollback()
            # Пробуем вставить пакет по одному
            print("🔄 Пытаемся вставить пакет по одному...")
            batch_added = 0
            for single_pair in batch:
                try:
                    cur.execute("""
                        INSERT INTO incompatibilities_non_models 
                        (property1_id, value1, property2_id, value2)
                        VALUES (?, ?, ?, ?)
                    """, single_pair)
                    batch_added += 1
                except Exception as single_e:
                    print(f"❌ Ошибка при вставке одиночной записи: {single_e}")
            added_count += batch_added
            conn.commit()
            print(f"✅ Вставлено {batch_added} записей из пакета")
    
    conn.close()
    
    total_time = time.time() - start_time
    print(f"\n📊 ИТОГИ:")
    print(f"✅ Успешно добавлено: {added_count}")
    print(f"🔍 Обнаружено дубликатов: {duplicates_found}")
    print(f"📈 Всего обработано пар: {len(incompatibility_pairs)}")
    print(f"⏱️  Общее время: {total_time:.1f} секунд")
    print(f"⚡ Скорость: {len(unique_pairs_list)/total_time:.1f} записей/сек")
    
    return added_count

def find_global_incompatibilities(db_file, output_csv=None):
    """
    Находит глобальные несовместимости (не зависящие от модели)
    """
    print("=== ПОИСК ГЛОБАЛЬНЫХ НЕСОВМЕСТИМОСТЕЙ ===")
    
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
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
    print(f"Найдены свойства: {list(property_ids.keys())}")
    
    # Подготавливаем данные для записи
    data_to_write = []
    total_incompatibilities = 0
    
    for prop1_name, prop2_name in property_pairs:
        prop1_id = property_ids.get(prop1_name)
        prop2_id = property_ids.get(prop2_name)
        
        if not prop1_id or not prop2_id:
            continue
        
        print(f"\n🔍 Проверяем: {prop1_name} ↔ {prop2_name}")
        
        # 1. Получаем ВСЕ возможные значения для этих свойств
        cur.execute("SELECT DISTINCT value FROM characteristics WHERE property_id = ?", (prop1_id,))
        all_values1 = [str(row[0]) for row in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT value FROM characteristics WHERE property_id = ?", (prop2_id,))
        all_values2 = [str(row[0]) for row in cur.fetchall()]
        
        if not all_values1 or not all_values2:
            continue
        
        print(f"   Всего значений: {prop1_name}={len(all_values1)}, {prop2_name}={len(all_values2)}")
        
        # 2. Получаем ВСЕ существующие комбинации (из всех моделей)
        cur.execute("""
        SELECT DISTINCT c1.value, c2.value
        FROM variants v
        JOIN characteristics c1 ON v.variant_id = c1.variant_id
        JOIN characteristics c2 ON v.variant_id = c2.variant_id
        WHERE v.model_id IN (
            SELECT model_id FROM models 
            WHERE model_name NOT LIKE '%#777%' 
            AND model_name NOT LIKE '%.Комплект О3%'
        )
        AND c1.property_id = ?
        AND c2.property_id = ?
        """, (prop1_id, prop2_id))
        
        existing_combinations = set((str(row[0]), str(row[1])) for row in cur.fetchall())
        print(f"   Существующие комбинации: {len(existing_combinations)}")
        
        # 3. Генерируем ВСЕ возможные комбинации
        all_possible_combinations = set(product(all_values1, all_values2))
        print(f"   Все возможные комбинации: {len(all_possible_combinations)}")
        
        # 4. Находим глобальные несовместимости (отсутствуют во всей базе)
        missing_combinations = all_possible_combinations - existing_combinations
        print(f"   Глобальные несовместимости: {len(missing_combinations)}")
        
        # 5. Записываем несовместимости (без указания модели)
        for val1, val2 in missing_combinations:
            data_to_write.append([ # вместо конкретной модели
                prop1_name,
                val1,
                prop2_name,
                val2
            ])
            total_incompatibilities += 1
        
        # Показываем примеры несовместимостей
        if missing_combinations:
            sample = list(missing_combinations)[:5]
            print(f"   Примеры несовместимостей:")
            for val1, val2 in sample:
                print(f"      🚫 {val1} ≠ {val2}")
    
    conn.close()
    
    # Сохраняем в CSV
    if output_csv and data_to_write:
        save_global_incompatibilities_to_csv(data_to_write, output_csv)
        print(f"\n💾 Результаты сохранены в: {output_csv}")
    
    print(f"\n🎯 ИТОГО: найдено {total_incompatibilities} глобальных несовместимостей")
    return data_to_write, total_incompatibilities


def get_or_create_property_id(cur, table_name, id_column, name_column, property_name):
    """
    Получает ID свойства, создает если не существует.
    """
    try:
        # Пытаемся найти существующее свойство
        cur.execute(f"SELECT {id_column} FROM {table_name} WHERE {name_column} = ?", (property_name,))
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        # Создаем новое свойство
        cur.execute(f"INSERT INTO {table_name} ({name_column}) VALUES (?)", (property_name,))
        
        # Получаем ID нового свойства
        cur.execute(f"SELECT {id_column} FROM {table_name} WHERE {name_column} = ?", (property_name,))
        result = cur.fetchone()
        
        if result:
            print(f"✅ Создано свойство: '{property_name}' с ID {result[0]}")
            return result[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при работе со свойством '{property_name}': {e}")
        return None


def save_global_incompatibilities_to_csv(data, filename):
    """
    Сохраняет глобальные несовместимости в CSV
    """
    headers = ["Модель", "Свойство 1", "Значение 1", "Свойство 2", "Значение 2", "Дата проверки"]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(headers)
        writer.writerows(data)
    
    print(f"📊 Сохранено {len(data)} несовместимостей")



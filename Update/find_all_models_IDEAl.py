import sqlite3
import csv
from datetime import datetime
from itertools import product

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


def check_and_append_to_existing_csv(db_file, existing_csv_file, output_csv=None):
    """
    Проверяет несовместимости и добавляет только новые в существующий CSV
    """
    print("=== ПРОВЕРКА И ДОБАВЛЕНИЕ НОВЫХ НЕСОВМЕСТИМОСТЕЙ ===")
    
    # Читаем существующие несовместимости из CSV
    existing_incompatibilities = set()
    try:
        with open(existing_csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            next(reader)  # пропускаем заголовок
            for row in reader:
                if len(row) >= 5:
                    # Создаем уникальный ключ: свойство1+значение1+свойство2+значение2
                    key = (row[1], row[2], row[3], row[4])
                    existing_incompatibilities.add(key)
        print(f"📚 Прочитано существующих несовместимостей: {len(existing_incompatibilities)}")
    except FileNotFoundError:
        print("📚 Существующий CSV файл не найден, начнем с чистого листа")
    
    # Находим все несовместимости
    all_incompatibilities, total_count = find_global_incompatibilities(db_file, None)
    
    # Фильтруем только новые несовместимости
    new_incompatibilities = []
    for row in all_incompatibilities:
        key = (row[1], row[2], row[3], row[4])  # свойство1, значение1, свойство2, значение2
        if key not in existing_incompatibilities:
            new_incompatibilities.append(row)
    
    print(f"🆕 Новых несовместимостей: {len(new_incompatibilities)}")
    
    # Сохраняем результаты
    if output_csv:
        if existing_incompatibilities:
            # Добавляем к существующим
            final_data = []
            # Читаем все существующие данные
            with open(existing_csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                headers = next(reader)
                final_data.append(headers)
                final_data.extend(reader)
            
            # Добавляем новые
            final_data.extend(new_incompatibilities)
            
            # Сохраняем обновленный файл
            with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerows(final_data)
            print(f"💾 Обновленный файл сохранен: {output_csv}")
        else:
            # Сохраняем только новые
            save_global_incompatibilities_to_csv(new_incompatibilities, output_csv)
    
    return new_incompatibilities, len(new_incompatibilities)


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




# Основной вызов
if __name__ == "__main__":
    db_file = "/home/alex/temp/doors.db"
    
    # Вариант 1: Найти все глобальные несовместимости
    output_csv = f"/home/alex/temp/incompatibilities_non_models.db.csv"
    results, count = find_global_incompatibilities(db_file, output_csv)
    
    # Вариант 2: Проверить и добавить только новые несовместимости
    # existing_csv = "existing_incompatibilities.csv"
    # new_results, new_count = check_and_append_to_existing_csv(db_file, existing_csv, "updated_incompatibilities.csv")
    
    
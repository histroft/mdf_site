import sqlite3
import csv
from datetime import datetime

def export_incompatibilities_to_csv(db_file, output_csv=None):
    """
    Выгружает таблицу Incompatibilities из базы данных в CSV файл
    """
    if output_csv is None:
        output_csv = f"/home/alex/temp/incompatibilities_export!!!!.csv"
    
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    try:
        # Получаем все данные из таблицы incompatibilities
        cur.execute("""
        SELECT 
            i.incompatibility_id,
            i.model_id,
            m.model_name,
            p1.property_name as property1_name,
            i.value1,
            p2.property_name as property2_name,
            i.value2
        FROM incompatibilities i
        LEFT JOIN models m ON i.model_id = m.model_id
        LEFT JOIN properties p1 ON i.property1_id = p1.property_id
        LEFT JOIN properties p2 ON i.property2_id = p2.property_id
        ORDER BY i.incompatibility_id
        """)
        
        data = cur.fetchall()
        
        if not data:
            print("❌ Таблица incompatibilities пуста")
            return None
        
        # Заголовки CSV
        headers = [
            "ID несовместимости",
            "ID модели", 
            "Название модели",
            "Свойство 1",
            "Значение 1",
            "Свойство 2", 
            "Значение 2"
        ]
        
        # Сохраняем в CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(headers)
            writer.writerows(data)
        
        print(f"✅ Таблица incompatibilities успешно выгружена в: {output_csv}")
        print(f"📊 Выгружено записей: {len(data)}")
        
        # Показываем статистику
        show_export_statistics(cur)
        
        return output_csv
        
    except Exception as e:
        print(f"❌ Ошибка при выгрузке: {e}")
        return None
    finally:
        conn.close()


def show_export_statistics(cur):
    """
    Показывает статистику по выгружаемым данным
    """
    # Общее количество записей
    cur.execute("SELECT COUNT(*) FROM incompatibilities")
    total_count = cur.fetchone()[0]
    
    # Количество записей с model_id = 0 (глобальные) и с конкретными моделями
    cur.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN model_id = 0 THEN 1 ELSE 0 END) as global_incompatibilities,
        SUM(CASE WHEN model_id > 0 THEN 1 ELSE 0 END) as model_specific_incompatibilities
    FROM incompatibilities
    """)
    
    stats = cur.fetchone()
    total, global_count, model_specific_count = stats
    
    # Статистика по парам свойств
    cur.execute("""
    SELECT 
        p1.property_name,
        p2.property_name,
        COUNT(*) as count
    FROM incompatibilities i
    JOIN properties p1 ON i.property1_id = p1.property_id
    JOIN properties p2 ON i.property2_id = p2.property_id
    GROUP BY p1.property_name, p2.property_name
    ORDER BY count DESC
    LIMIT 10
    """)
    
    top_pairs = cur.fetchall()
    
    print(f"\n📈 СТАТИСТИКА ВЫГРУЗКИ:")
    print(f"   📊 Всего несовместимостей: {total_count}")
    print(f"   🌍 Глобальные несовместимости (model_id=0): {global_count}")
    print(f"   📦 Привязанные к моделям: {model_specific_count}")
    
    if top_pairs:
        print(f"\n   🔝 Топ-10 пар свойств по количеству несовместимостей:")
        for i, (prop1, prop2, count) in enumerate(top_pairs, 1):
            print(f"      {i}. {prop1} ↔ {prop2}: {count} несовместимостей")


def export_filtered_incompatibilities(db_file, model_id=None, property_pair=None, output_csv=None):
    """
    Выгружает отфильтрованные несовместимости в CSV
    """
    if output_csv is None:
        suffix = ""
        if model_id is not None:
            suffix += f"_model_{model_id}"
        if property_pair is not None:
            suffix += f"_{property_pair[0]}_{property_pair[1]}"
        output_csv = f"incompatibilities_filtered{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    try:
        # Базовый запрос
        query = """
        SELECT 
            i.incompatibility_id,
            i.model_id,
            m.model_name,
            p1.property_name as property1_name,
            i.value1,
            p2.property_name as property2_name,
            i.value2
        FROM incompatibilities i
        LEFT JOIN models m ON i.model_id = m.model_id
        LEFT JOIN properties p1 ON i.property1_id = p1.property_id
        LEFT JOIN properties p2 ON i.property2_id = p2.property_id
        WHERE 1=1
        """
        
        params = []
        
        # Добавляем фильтры
        if model_id is not None:
            query += " AND i.model_id = ?"
            params.append(model_id)
        
        if property_pair is not None:
            prop1_name, prop2_name = property_pair
            query += " AND p1.property_name = ? AND p2.property_name = ?"
            params.extend([prop1_name, prop2_name])
        
        query += " ORDER BY i.incompatibility_id"
        
        cur.execute(query, params)
        data = cur.fetchall()
        
        if not data:
            print("❌ Нет данных по указанным фильтрам")
            return None
        
        headers = [
            "ID несовместимости",
            "ID модели", 
            "Название модели",
            "Свойство 1",
            "Значение 1",
            "Свойство 2", 
            "Значение 2"
        ]
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(headers)
            writer.writerows(data)
        
        print(f"✅ Отфильтрованные данные выгружены в: {output_csv}")
        print(f"📊 Выгружено записей: {len(data)}")
        
        return output_csv
        
    except Exception as e:
        print(f"❌ Ошибка при выгрузке: {e}")
        return None
    finally:
        conn.close()


def preview_incompatibilities(db_file, limit=10):
    """
    Показывает превью данных из таблицы incompatibilities
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT 
            i.incompatibility_id,
            CASE 
                WHEN i.model_id = 0 THEN 'Глобальная'
                ELSE m.model_name 
            END as model_info,
            p1.property_name,
            i.value1,
            p2.property_name,
            i.value2
        FROM incompatibilities i
        LEFT JOIN models m ON i.model_id = m.model_id
        LEFT JOIN properties p1 ON i.property1_id = p1.property_id
        LEFT JOIN properties p2 ON i.property2_id = p2.property_id
        ORDER BY i.incompatibility_id
        LIMIT ?
        """, (limit,))
        
        data = cur.fetchall()
        
        if not data:
            print("❌ Таблица incompatibilities пуста")
            return
        
        print(f"\n👀 ПРЕВЬЮ ТАБЛИЦЫ INCOMPATIBILITIES (первые {limit} записей):")
        print("-" * 80)
        for row in data:
            inc_id, model_info, prop1, val1, prop2, val2 = row
            print(f"ID: {inc_id} | Модель: {model_info}")
            print(f"   {prop1} = '{val1}' ❌ {prop2} = '{val2}'")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Ошибка при просмотре: {e}")
    finally:
        conn.close()


# Основной вызов
if __name__ == "__main__":
    db_file = '/home/alex/temp/doors.db'
    
    # 1. Показываем превью данных
    preview_incompatibilities(db_file, limit=5)
    
    # 2. Выгружаем всю таблицу
    csv_file = export_incompatibilities_to_csv(db_file)
    

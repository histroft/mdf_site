import sqlite3


def find_variants_with_properties(db_file, prop1_name, prop1_value, prop2_name, prop2_value, model_name=None):
    """
    Находит исполнения, где встречаются два заданных свойства характеристик
    
    Args:
        db_file: путь к базе данных
        prop1_name: название первого свойства
        prop1_value: значение первого свойства  
        prop2_name: название второго свойства
        prop2_value: значение второго свойства
        model_name: опционально - название конкретной модели для фильтрации
    
    Returns:
        список найденных исполнений
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    print(f"🔍 Поиск исполнений с свойствами:")
    print(f"   {prop1_name} = '{prop1_value}'")
    print(f"   {prop2_name} = '{prop2_value}'")
    if model_name:
        print(f"   Модель: '{model_name}'")
    
    try:
        # Базовый запрос для поиска исполнений
        query = """
        SELECT DISTINCT
            m.model_name,
            v.variant_id,
            v.unique_combination,
            c1.value as value1,
            c2.value as value2
        FROM variants v
        JOIN models m ON v.model_id = m.model_id
        JOIN characteristics c1 ON v.variant_id = c1.variant_id
        JOIN characteristics c2 ON v.variant_id = c2.variant_id
        JOIN properties p1 ON c1.property_id = p1.property_id
        JOIN properties p2 ON c2.property_id = p2.property_id
        WHERE p1.property_name = ? AND c1.value = ?
          AND p2.property_name = ? AND c2.value = ?
          AND v.unique_combination NOT LIKE '%#777%'
        """
        
        params = [prop1_name, prop1_value, prop2_name, prop2_value]
        
        # Добавляем фильтр по модели если указан
        if model_name:
            query += " AND m.model_name = ?"
            params.append(model_name)
        
        query += " ORDER BY m.model_name, v.variant_id"
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        if results:
            print(f"✅ Найдено исполнений: {len(results)}")
            for i, (model, variant_id, combination, val1, val2) in enumerate(results, 1):
                print(f"\n   {i}. 📦 Модель: {model}")
                print(f"      🔢 ID исполнения: {variant_id}")
                print(f"      🏷️ Комбинация: {combination}")
                print(f"      📋 {prop1_name} = '{val1}'")
                print(f"      📋 {prop2_name} = '{val2}'")
        else:
            print("❌ Исполнения с указанными свойствами не найдены")
            
        return results
        
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        return []
    finally:
        conn.close()


def find_variants_with_properties_detailed(db_file, prop1_name, prop1_value, prop2_name, prop2_value, model_name=None):
    """
    Находит исполнения с подробной информацией о всех характеристиках
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    print(f"🔍 Детальный поиск исполнений:")
    print(f"   {prop1_name} = '{prop1_value}'")
    print(f"   {prop2_name} = '{prop2_value}'")
    
    try:
        # Поиск исполнений
        query = """
        SELECT DISTINCT v.variant_id
        FROM variants v
        JOIN characteristics c1 ON v.variant_id = c1.variant_id
        JOIN characteristics c2 ON v.variant_id = c2.variant_id
        JOIN properties p1 ON c1.property_id = p1.property_id
        JOIN properties p2 ON c2.property_id = p2.property_id
        JOIN models m ON v.model_id = m.model_id
        WHERE p1.property_name = ? AND c1.value = ?
          AND p2.property_name = ? AND c2.value = ?
          AND v.unique_combination NOT LIKE '%#777%'
        """
        
        params = [prop1_name, prop1_value, prop2_name, prop2_value]
        
        if model_name:
            query += " AND m.model_name = ?"
            params.append(model_name)
            
        cur.execute(query, params)
        variant_ids = [row[0] for row in cur.fetchall()]
        
        if not variant_ids:
            print("❌ Исполнения не найдены")
            return []
        
        print(f"✅ Найдено исполнений: {len(variant_ids)}")
        
        # Для каждого найденного исполнения получаем полную информацию
        detailed_results = []
        for variant_id in variant_ids:
            cur.execute("""
            SELECT 
                m.model_name,
                v.unique_combination,
                p.property_name,
                c.value
            FROM variants v
            JOIN models m ON v.model_id = m.model_id
            JOIN characteristics c ON v.variant_id = c.variant_id
            JOIN properties p ON c.property_id = p.property_id
            WHERE v.variant_id = ?
            ORDER BY p.property_name
            """, (variant_id,))
            
            variant_data = cur.fetchall()
            if variant_data:
                model_name = variant_data[0][0]
                combination = variant_data[0][1]
                
                print(f"\n   📦 Модель: {model_name}")
                print(f"      🔢 ID исполнения: {variant_id}")
                print(f"      🏷️ Комбинация: {combination}")
                print(f"      📋 Все характеристики:")
                
                characteristics = {}
                for prop_name, value in [(row[2], row[3]) for row in variant_data]:
                    characteristics[prop_name] = value
                    print(f"         🔧 {prop_name} = '{value}'")
                
                detailed_results.append({
                    'variant_id': variant_id,
                    'model_name': model_name,
                    'combination': combination,
                    'characteristics': characteristics
                })
        
        return detailed_results
        
    except Exception as e:
        print(f"❌ Ошибка при детальном поиске: {e}")
        return []
    finally:
        conn.close()


def check_properties_existence(db_file, prop1_name, prop1_value, prop2_name, prop2_value):
    """
    Проверяет существование свойств и их значений в базе
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    print(f"🔍 ПРОВЕРКА СУЩЕСТВОВАНИЯ СВОЙСТВ:")
    
    try:
        # Проверяем существование свойств
        cur.execute("SELECT property_id FROM properties WHERE property_name = ?", (prop1_name,))
        prop1_exists = cur.fetchone() is not None
        
        cur.execute("SELECT property_id FROM properties WHERE property_name = ?", (prop2_name,))
        prop2_exists = cur.fetchone() is not None
        
        print(f"   Свойство '{prop1_name}': {'✅ найдено' if prop1_exists else '❌ не найдено'}")
        print(f"   Свойство '{prop2_name}': {'✅ найдено' if prop2_exists else '❌ не найдено'}")
        
        if not prop1_exists or not prop2_exists:
            return False
        
        # Проверяем существование значений
        cur.execute("""
        SELECT DISTINCT c.value 
        FROM characteristics c
        JOIN properties p ON c.property_id = p.property_id
        WHERE p.property_name = ? AND c.value = ?
        LIMIT 1
        """, (prop1_name, prop1_value))
        value1_exists = cur.fetchone() is not None
        
        cur.execute("""
        SELECT DISTINCT c.value 
        FROM characteristics c
        JOIN properties p ON c.property_id = p.property_id
        WHERE p.property_name = ? AND c.value = ?
        LIMIT 1
        """, (prop2_name, prop2_value))
        value2_exists = cur.fetchone() is not None
        
        print(f"   Значение '{prop1_value}': {'✅ найдено' if value1_exists else '❌ не найдено'}")
        print(f"   Значение '{prop2_value}': {'✅ найдено' if value2_exists else '❌ не найдено'}")
        
        return value1_exists and value2_exists
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
        return False
    finally:
        conn.close()


# Примеры использования
if __name__ == "__main__":
    db_file = "/home/alex/DB/doors.db"
    
    # 1. Проверка существования свойств
    print("=== ПРОВЕРКА СУЩЕСТВОВАНИЯ ===")
    properties_exist = check_properties_existence(
        db_file,
        "04_Лицо (цвет)", "ЛКП Бруно",
        "05_Лицо (рисунок)", "Sunrise"
    )
    
    if properties_exist:
        print("\n=== ПОИСК ИСПОЛНЕНИЙ ===")
        # 2. Простой поиск
        results = find_variants_with_properties(
            db_file,
            "04_Лицо (цвет)", "ЛКП Бруно", 
            "05_Лицо (рисунок)", "Sunrise"
        )
        
        # 3. Детальный поиск
        print("\n=== ДЕТАЛЬНЫЙ ПОИСК ===")
        detailed_results = find_variants_with_properties_detailed(
            db_file,
            "04_Лицо (цвет)", "ЛКП Бруно",
            "05_Лицо (рисунок)", "Sunrise"
        )
        
       

import sqlite3

def get_model_characteristics(db_path, model_name):
    """
    Возвращает характеристики модели в формате для фронтенда
    
    Параметры:
        db_path: путь к базе данных
        model_name: название модели (например, "CYBER PRO MP")
    
    Возвращает:
        Словарь с характеристиками в формате:
        {
            "01_Ширина": ["1000", "1030", "880", "950"],
            "02_Высота": ["2050", "2070", "2100", "2150", "2200"],
            ...
        }
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Получаем model_id по названию модели
        cursor.execute('''
            SELECT model_id 
            FROM models 
            WHERE model_name = ?
        ''', (model_name,))
        
        model_row = cursor.fetchone()
        if not model_row:
            print(f"Модель '{model_name}' не найдена в базе данных")
            conn.close()
            return {}
        
        model_id = model_row[0]
        print(f"Found model_id: {model_id} for {model_name}")
        
        # Ищем вариант с #777 (основной вариант) или любой другой
        cursor.execute('''
            SELECT v.variant_id 
            FROM variants v
            WHERE v.model_id = ? 
            ORDER BY 
                CASE WHEN v.unique_combination LIKE '%#777%' THEN 0 ELSE 1 END,
                v.variant_id
            LIMIT 1
        ''', (model_id,))
        
        variant_row = cursor.fetchone()
        if not variant_row:
            print(f"Варианты для модели {model_name} не найдены")
            conn.close()
            return {}
        
        variant_id = variant_row[0]
        print(f"Using variant_id: {variant_id}")
        
        # Получаем все характеристики для этого варианта
        cursor.execute('''
            SELECT p.property_name, GROUP_CONCAT(DISTINCT c.value) as values_list
            FROM characteristics c
            JOIN properties p ON c.property_id = p.property_id
            WHERE c.variant_id = ?
            GROUP BY p.property_name
            ORDER BY p.property_name
        ''', (variant_id,))
        
        characteristics = {}
        for prop_name, values_str in cursor.fetchall():
            if values_str:
                # Разделяем значения (могут быть разделены запятыми)
                values = [v.strip() for v in values_str.split(',')]
                characteristics[prop_name] = values
            else:
                characteristics[prop_name] = []
        
        conn.close()
        
        print(f"Loaded {len(characteristics)} characteristics for {model_name}")
        return characteristics
        
    except Exception as e:
        print(f"Ошибка при получении характеристик: {str(e)}")
        import traceback
        traceback.print_exc()
        conn.close()
        return {}

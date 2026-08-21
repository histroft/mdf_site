import sqlite3

def GetListModel(name_db) -> list:
    """
    Возвращает список всех моделей дверей из базы данных
    Параметры: name_db - имя и путь к БазеДанных
    Возвращает: Список названий моделей (list[str])
    """
    # Модели, которые нужно скрыть
    models_to_hide = [
        'TAU LT МP', 'TAU LT PP', 'TAU PRO PP', 'TAU PRO MP',
        'DELTA LT PP', 'DELTA LT MP', 'SNEGIR HOME',
        'DELTA MP FDL-EI 30', 'DELTA PP FDL-EI 30',
        'DELTA MP FDL-EI 60', 'DELTA PP FDL-EI 60',
        'ALFA LT PP', 'DIAMOND FS','Надставка','Надставка Термо',
         'Надставка ARCTIC'
    ]
    
    conn = sqlite3.connect(name_db)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT model_name FROM models ORDER BY model_name")
        all_models = [row[0] for row in cursor.fetchall()]
        
        # Фильтруем список, исключая модели из models_to_hide
        models = [model for model in all_models if model not in models_to_hide]
        
        conn.close()
        return models

    except Exception as e:
        print(f"Ошибка при получении списка моделей: {str(e)}")
        conn.close()
        return []


if __name__ == '__main__':
    name = 'database/doors.db'
    # Получаем список всех моделей
    models_list = GetListModel(name)
    print(f"Всего моделей: {len(models_list)}")
    print("-" * 50)
    for model in models_list:
        print(f"- {model}")
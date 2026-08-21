import sqlite3

def clear_database_with_vacuum(db_path):
    """Очистка всех таблиц и освобождение места с помощью VACUUM"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        # Удаляем все таблицы
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        # Выполняем VACUUM для освобождения места
        cursor.execute("VACUUM")
        
        conn.commit()
        print("База данных полностью очищена и пространство освобождено")
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
    finally:
        conn.close()

# Использование
if __name__=='__main__':
    db_name='/home/alex/temp/doors.db'
    clear_database_with_vacuum(db_name)
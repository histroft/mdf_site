import os
import sqlite3

def delete_database_file(db_path):
    """Удаляет файл базы данных"""
    try:
        # Закрываем все соединения с базой
        sqlite3.connect(db_path).close()
        
        # Удаляем файл
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ Файл базы данных '{db_path}' успешно удален")
        else:
            print(f"⚠️ Файл '{db_path}' не существует")
            
    except Exception as e:
        print(f"❌ Ошибка при удалении файла: {e}")

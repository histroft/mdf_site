
import sqlite3

db_path = "database/doors.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Получаем все таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 60)
print("СТРУКТУРА БАЗЫ ДАННЫХ")
print("=" * 60)

for table in tables:
    table_name = table[0]
    print(f"\n📋 Таблица: {table_name}")
    print("-" * 40)
    
    # Получаем структуру таблицы
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    for col in columns:
        col_id, col_name, col_type, not_null, default, pk = col
        print(f"  {col_id}: {col_name} ({col_type}) {'PK' if pk else ''}")
    
    # Показываем первые 3 строки
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
    rows = cursor.fetchall()
    
    if rows:
        print(f"\n  Пример данных (первые {len(rows)} строк):")
        col_names = [col[1] for col in columns]
        for row in rows:
            print(f"    {dict(zip(col_names, row))}")
    else:
        print(f"\n  Таблица пуста")

conn.close()
